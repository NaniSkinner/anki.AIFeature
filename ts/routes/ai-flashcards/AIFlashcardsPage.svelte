<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<script lang="ts">
    import type { DeckNameId } from "@generated/anki/decks_pb";
    import { importApprovedCards, saveSession, clearSession } from "@generated/backend";
    import { bridgeCommand } from "@tslib/bridgecommand";
    import { onMount } from "svelte";

    import Container from "$lib/components/Container.svelte";
    import EnumSelector from "$lib/components/EnumSelector.svelte";

    import "./ai-flashcards-base.scss";
    import SourceSelector from "./SourceSelector.svelte";
    import CardReview from "./CardReview.svelte";
    import Header from "./Header.svelte";

    // Variables for async generation callback
    let pendingGenerateResolve: ((cards: SimpleCard[]) => void) | null = null;
    let pendingGenerateReject: ((error: Error) => void) | null = null;

    // Signal to Python that the page is ready and set up async callback
    onMount(() => {
        bridgeCommand(`ai_flashcards:${JSON.stringify({ action: "ready" })}`);

        // Register global callback for Python to call when generation completes
        // This is needed because OpenAI API call runs in background thread
        (window as any)._aiFlashcardsOnGenerate = (result: {
            cards?: SimpleCard[];
            error?: string;
        }) => {
            if (result.error) {
                pendingGenerateReject?.(new Error(result.error));
            } else {
                pendingGenerateResolve?.(result.cards || []);
            }
            pendingGenerateResolve = null;
            pendingGenerateReject = null;
        };
    });

    // Simple card interface matching our proto
    interface SimpleCard {
        id: string;
        cardType: number;
        front: string;
        back: string;
        suggestedTags: string[];
        status: number;
    }

    // Simple session interface
    interface SimpleSession {
        hasSession: boolean;
        cards: SimpleCard[];
        sourceName: string;
        sourceText: string;
    }

    export let decks: { entries: DeckNameId[] };
    export let session: SimpleSession;

    type Step = "source" | "generating" | "review" | "importing" | "done";

    let currentStep: Step = session.hasSession ? "review" : "source";
    let cards: SimpleCard[] = session.hasSession ? session.cards : [];
    let sourceName = session.sourceName || "";
    let sourceText = session.sourceText || "";
    let sourceUrl = "";
    let selectedDeckId = decks.entries[0]?.id || 0n;
    let error: string | null = null;
    let importResult: { imported: number; duplicates: number } | null = null;

    $: approvedCount = cards.filter((c) => c.status === 1).length;
    $: rejectedCount = cards.filter((c) => c.status === 2).length;
    $: pendingCount = cards.filter((c) => c.status === 0).length;

    async function handleGenerate(text: string, name: string, url: string) {
        console.log("[AIFlashcardsPage] handleGenerate called");
        console.log("[AIFlashcardsPage] text length:", text.length, "name:", name);
        sourceText = text;
        sourceName = name;
        sourceUrl = url;
        currentStep = "generating";
        error = null;

        try {
            // Call Python backend for generation (via pycmd bridge)
            console.log("[AIFlashcardsPage] Calling generateFlashcardsViaBackend");
            const generatedCards = await generateFlashcardsViaBackend(text, name);
            console.log("[AIFlashcardsPage] Received cards:", generatedCards.length);
            cards = generatedCards;
            currentStep = "review";

            // Save session for persistence
            await saveSession({
                sourceName: name,
                sourceText: text,
                cards: cards as any,
            });
        } catch (e) {
            console.error("[AIFlashcardsPage] Error in handleGenerate:", e);
            error = e instanceof Error ? e.message : String(e);
            currentStep = "source";
        }
    }

    async function generateFlashcardsViaBackend(
        text: string,
        name: string,
    ): Promise<SimpleCard[]> {
        console.log("[AIFlashcardsPage] generateFlashcardsViaBackend called");
        // This will call the Python layer via bridgeCommand
        // The Python layer runs OpenAI API in background thread and calls
        // window._aiFlashcardsOnGenerate when done
        return new Promise((resolve, reject) => {
            pendingGenerateResolve = resolve;
            pendingGenerateReject = reject;

            const request = {
                action: "generate_flashcards",
                text,
                sourceName: name,
            };

            console.log("[AIFlashcardsPage] Sending bridgeCommand");
            bridgeCommand<string>(
                `ai_flashcards:${JSON.stringify(request)}`,
                (response: string) => {
                    console.log("[AIFlashcardsPage] bridgeCommand response:", response);
                    try {
                        const result = JSON.parse(response);
                        // If immediate error (like missing API key), reject now
                        if (result.error) {
                            console.error("[AIFlashcardsPage] Immediate error:", result.error);
                            pendingGenerateResolve = null;
                            pendingGenerateReject = null;
                            reject(new Error(result.error));
                        } else {
                            console.log("[AIFlashcardsPage] Status:", result.status, "- waiting for callback");
                        }
                        // If status is "generating", wait for _aiFlashcardsOnGenerate callback
                        // (resolve/reject will be called by the global callback)
                    } catch (e) {
                        console.error("[AIFlashcardsPage] Error parsing response:", e);
                        pendingGenerateResolve = null;
                        pendingGenerateReject = null;
                        reject(e);
                    }
                },
            );

            // Timeout after 2 minutes
            setTimeout(() => {
                if (pendingGenerateResolve) {
                    console.error("[AIFlashcardsPage] Generation timed out");
                    pendingGenerateResolve = null;
                    pendingGenerateReject = null;
                    reject(new Error("Generation timed out after 2 minutes"));
                }
            }, 120000);
        });
    }

    function handleCardUpdate(cardId: string, status: number) {
        cards = cards.map((card) => (card.id === cardId ? { ...card, status } : card));

        // Auto-save session on changes
        saveSession({
            sourceName,
            sourceText,
            cards: cards as any,
        }).catch(console.error);
    }

    async function handleImport() {
        if (approvedCount === 0) {
            error = "No cards have been approved yet.";
            return;
        }

        currentStep = "importing";
        error = null;

        try {
            const result = await importApprovedCards({
                cards: cards.filter((c) => c.status === 1) as any,
                targetDeckId: selectedDeckId,
                additionalTags: [],
            });

            importResult = {
                imported: result.importedCount,
                duplicates: result.duplicateCount,
            };

            // Clear session after successful import
            await clearSession({});
            currentStep = "done";
        } catch (e) {
            error = e instanceof Error ? e.message : String(e);
            currentStep = "review";
        }
    }

    function handleNewSession() {
        cards = [];
        sourceName = "";
        sourceText = "";
        error = null;
        importResult = null;
        currentStep = "source";
        clearSession({}).catch(console.error);
    }

    function approveAll() {
        cards = cards.map((card) => ({ ...card, status: 1 }));
        saveSession({ sourceName, sourceText, cards: cards as any }).catch(
            console.error,
        );
    }

    function rejectAll() {
        cards = cards.map((card) => ({ ...card, status: 2 }));
        saveSession({ sourceName, sourceText, cards: cards as any }).catch(
            console.error,
        );
    }
</script>

<div class="ai-flashcards-page">
    <Header
        title="AI Flashcard Generator"
        showNewButton={currentStep !== "source"}
        on:new={handleNewSession}
    />

    {#if currentStep === "source"}
        <Container breakpoint="md">
            <SourceSelector
                initialText={sourceText}
                initialSourceName={sourceName}
                initialUrl={sourceUrl}
                on:generate={(e) =>
                    handleGenerate(e.detail.text, e.detail.name, e.detail.url)}
            />
        </Container>
    {:else if currentStep === "generating"}
        <Container breakpoint="md">
            <div class="progress-indicator">
                <div class="spinner"></div>
                <p>Generating flashcards...</p>
            </div>
        </Container>
    {:else if currentStep === "review"}
        <div class="stats-bar">
            <div class="stat">
                <span class="label">Pending:</span>
                <span class="value">{pendingCount}</span>
            </div>
            <div class="stat">
                <span class="label">Approved:</span>
                <span class="value">{approvedCount}</span>
            </div>
            <div class="stat">
                <span class="label">Rejected:</span>
                <span class="value">{rejectedCount}</span>
            </div>
        </div>

        {#if error}
            <div class="error-message">{error}</div>
        {/if}

        <CardReview
            {cards}
            on:approve={(e) => handleCardUpdate(e.detail.id, 1)}
            on:reject={(e) => handleCardUpdate(e.detail.id, 2)}
            on:reset={(e) => handleCardUpdate(e.detail.id, 0)}
        />

        <div class="bottom-bar">
            <div class="import-options">
                <span>Target Deck:</span>
                <EnumSelector
                    bind:value={selectedDeckId}
                    choices={decks.entries.map((d) => ({ label: d.name, value: d.id }))}
                />
            </div>
            <div class="card-actions">
                <button class="btn" on:click={approveAll}>Approve All</button>
                <button class="btn" on:click={rejectAll}>Reject All</button>
                <button
                    class="btn btn-primary"
                    disabled={approvedCount === 0}
                    on:click={handleImport}
                >
                    Import Approved ({approvedCount})
                </button>
            </div>
        </div>
    {:else if currentStep === "importing"}
        <Container breakpoint="md">
            <div class="progress-indicator">
                <div class="spinner"></div>
                <p>Importing cards...</p>
            </div>
        </Container>
    {:else if currentStep === "done"}
        <Container breakpoint="md">
            <div class="success-message">
                <h3>Import Complete!</h3>
                {#if importResult}
                    <p>
                        {importResult.imported} card{importResult.imported !== 1
                            ? "s"
                            : ""} imported
                        {#if importResult.duplicates > 0}
                            ({importResult.duplicates} duplicate{importResult.duplicates !==
                            1
                                ? "s"
                                : ""} skipped)
                        {/if}
                    </p>
                {/if}
                <button class="btn btn-primary" on:click={handleNewSession}>
                    Start New Generation
                </button>
            </div>
        </Container>
    {/if}
</div>
