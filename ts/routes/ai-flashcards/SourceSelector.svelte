<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import { bridgeCommand } from "@tslib/bridgecommand";

    import TitledContainer from "$lib/components/TitledContainer.svelte";
    import Row from "$lib/components/Row.svelte";

    const dispatch = createEventDispatcher<{
        generate: { text: string; name: string; url: string };
    }>();

    // Props for restoring state when returning from error
    export let initialText = "";
    export let initialSourceName = "";
    export let initialUrl = "";

    let sourceType: "file" | "text" | "url" = "text";
    let textInput = initialText;
    let urlInput = initialUrl;
    let sourceName = initialSourceName;
    let fileInput: HTMLInputElement;
    let dragging = false;
    let isLoading = false;
    let error: string | null = null;

    async function handleFileSelect(event: Event) {
        const input = event.target as HTMLInputElement;
        if (input.files && input.files[0]) {
            await processFile(input.files[0]);
        }
    }

    async function handleDrop(event: DragEvent) {
        event.preventDefault();
        dragging = false;

        if (event.dataTransfer?.files && event.dataTransfer.files[0]) {
            await processFile(event.dataTransfer.files[0]);
        }
    }

    async function processFile(file: File) {
        isLoading = true;
        error = null;

        try {
            sourceName = file.name;

            // Read file content - for now just handle text files
            // PDF and other formats will be handled by Python backend
            if (
                file.type.startsWith("text/") ||
                file.name.endsWith(".txt") ||
                file.name.endsWith(".md")
            ) {
                textInput = await file.text();
                sourceType = "text";
            } else {
                // For PDFs and other files, we'll send the file path to Python
                // This is a simplified version - real implementation would use file picker
                error =
                    "This file type is not yet supported. Please use TXT or MD files.";
            }
        } catch (e) {
            error = e instanceof Error ? e.message : String(e);
        } finally {
            isLoading = false;
        }
    }

    async function handleUrlFetch() {
        if (!urlInput.trim()) {
            return;
        }

        isLoading = true;
        error = null;

        try {
            // Call Python backend to fetch and parse URL content
            const result = await fetchUrlViaBackend(urlInput.trim());
            textInput = result.text;
            sourceName = result.sourceName || urlInput;
            sourceType = "text"; // Switch to text tab to show the fetched content
        } catch (e) {
            error = e instanceof Error ? e.message : String(e);
        } finally {
            isLoading = false;
        }
    }

    async function fetchUrlViaBackend(
        url: string,
    ): Promise<{ text: string; sourceName: string }> {
        return new Promise((resolve, reject) => {
            const request = {
                action: "fetch_url",
                url,
            };

            bridgeCommand<string>(
                `ai_flashcards:${JSON.stringify(request)}`,
                (response: string) => {
                    try {
                        const result = JSON.parse(response);
                        if (result.error) {
                            reject(new Error(result.error));
                        } else {
                            resolve({
                                text: result.text || "",
                                sourceName: result.sourceName || url,
                            });
                        }
                    } catch (e) {
                        reject(e);
                    }
                },
            );
        });
    }

    function handleGenerate() {
        console.log("[SourceSelector] handleGenerate called");
        console.log("[SourceSelector] textInput length:", textInput.length);
        if (!textInput.trim()) {
            error = "Please provide text to generate flashcards from.";
            return;
        }

        console.log("[SourceSelector] Dispatching generate event");
        dispatch("generate", {
            text: textInput,
            name: sourceName || "Untitled",
            url: urlInput,
        });
    }

    function handleDragOver(event: DragEvent) {
        event.preventDefault();
        dragging = true;
    }

    function handleDragLeave() {
        dragging = false;
    }
</script>

<div class="source-selector">
    <Row class="d-block">
        <TitledContainer title="Select Source Material">
            <div class="source-tabs">
                <button
                    class="tab"
                    class:active={sourceType === "text"}
                    on:click={() => (sourceType = "text")}
                >
                    Text
                </button>
                <button
                    class="tab"
                    class:active={sourceType === "file"}
                    on:click={() => (sourceType = "file")}
                >
                    File
                </button>
                <button
                    class="tab"
                    class:active={sourceType === "url"}
                    on:click={() => (sourceType = "url")}
                >
                    URL
                </button>
            </div>

            {#if sourceType === "text"}
                <div class="text-input-area">
                    <input
                        type="text"
                        class="form-control"
                        placeholder="Source name (optional)"
                        bind:value={sourceName}
                    />
                    <textarea
                        class="form-control"
                        placeholder="Paste or type your text here..."
                        bind:value={textInput}
                    ></textarea>
                </div>
            {:else if sourceType === "file"}
                <div
                    class="file-input-area"
                    class:dragging
                    on:dragover={handleDragOver}
                    on:dragleave={handleDragLeave}
                    on:drop={handleDrop}
                    on:click={() => fileInput.click()}
                    role="button"
                    tabindex="0"
                    on:keydown={(e) => e.key === "Enter" && fileInput.click()}
                >
                    <input
                        type="file"
                        accept=".txt,.md,.pdf,.html"
                        style="display: none"
                        bind:this={fileInput}
                        on:change={handleFileSelect}
                    />
                    <p>Drag and drop a file here, or click to select</p>
                    <p class="supported-formats">
                        Supported formats: TXT, MD, PDF, HTML
                    </p>
                </div>
            {:else if sourceType === "url"}
                <div class="url-input-area">
                    <div class="url-row">
                        <input
                            type="url"
                            class="form-control"
                            placeholder="Enter a URL to fetch content from"
                            bind:value={urlInput}
                        />
                        <button
                            class="btn"
                            on:click={handleUrlFetch}
                            disabled={isLoading}
                        >
                            Fetch
                        </button>
                    </div>
                </div>
            {/if}

            {#if error}
                <div class="error-message">{error}</div>
            {/if}

            {#if isLoading}
                <div class="loading">
                    <span class="spinner"></span>
                    Loading...
                </div>
            {/if}
        </TitledContainer>
    </Row>

    <div class="generate-button-container">
        <button
            class="btn btn-primary btn-lg"
            disabled={!textInput.trim() || isLoading}
            on:click={handleGenerate}
        >
            Generate Flashcards
        </button>
    </div>
</div>

<style lang="scss">
    .source-tabs {
        display: flex;
        gap: 0;
        margin-bottom: 1rem;
        border-bottom: 1px solid var(--border);

        .tab {
            padding: 0.5rem 1rem;
            border: none;
            background: none;
            cursor: pointer;
            color: var(--fg-subtle);
            border-bottom: 2px solid transparent;
            margin-bottom: -1px;

            &.active {
                color: var(--fg);
                border-bottom-color: var(--accent);
            }

            &:hover:not(.active) {
                color: var(--fg);
            }
        }
    }

    .url-input-area {
        .url-row {
            display: flex;
            gap: 0.5rem;

            input {
                flex: 1;
            }
        }
    }

    .supported-formats {
        font-size: 0.875rem;
        color: var(--fg-subtle);
        margin-top: 0.5rem;
    }

    .loading {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem;
        color: var(--fg-subtle);

        .spinner {
            width: 16px;
            height: 16px;
            border: 2px solid var(--border);
            border-top-color: var(--accent);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
    }

    @keyframes spin {
        to {
            transform: rotate(360deg);
        }
    }

    .generate-button-container {
        display: flex;
        justify-content: center;
        margin-top: 1rem;

        .btn-lg {
            padding: 0.75rem 2rem;
            font-size: 1.1rem;
        }
    }
</style>
