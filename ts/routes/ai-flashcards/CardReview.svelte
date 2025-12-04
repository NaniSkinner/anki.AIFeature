<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<script lang="ts">
    import { createEventDispatcher } from "svelte";

    // Simple card interface
    interface SimpleCard {
        id: string;
        cardType: number;
        front: string;
        back: string;
        suggestedTags: string[];
        status: number;
    }

    export let cards: SimpleCard[];

    const dispatch = createEventDispatcher<{
        approve: { id: string };
        reject: { id: string };
        reset: { id: string };
    }>();

    function getCardTypeName(type: number): string {
        switch (type) {
            case 0:
                return "Basic";
            case 1:
                return "Basic (and reversed)";
            case 2:
                return "Cloze";
            default:
                return "Unknown";
        }
    }

    function getStatusClass(status: number): string {
        switch (status) {
            case 1:
                return "approved";
            case 2:
                return "rejected";
            default:
                return "";
        }
    }

    function formatCloze(text: string): string {
        // Format cloze deletions for display: {{c1::text}} -> [text]
        return text.replace(
            /\{\{c\d+::([^}]+)\}\}/g,
            "<span class='cloze'>[$1]</span>",
        );
    }
</script>

<div class="card-list">
    {#each cards as card (card.id)}
        <div class="card-item {getStatusClass(card.status)}">
            <div class="card-header">
                <span class="card-type-badge">{getCardTypeName(card.cardType)}</span>
                <div class="card-actions">
                    {#if card.status === 0}
                        <button
                            class="btn btn-sm btn-success"
                            on:click={() => dispatch("approve", { id: card.id })}
                            title="Approve"
                        >
                            &#10003;
                        </button>
                        <button
                            class="btn btn-sm btn-danger"
                            on:click={() => dispatch("reject", { id: card.id })}
                            title="Reject"
                        >
                            &#10005;
                        </button>
                    {:else}
                        <button
                            class="btn btn-sm"
                            on:click={() => dispatch("reset", { id: card.id })}
                            title="Reset"
                        >
                            &#8634;
                        </button>
                    {/if}
                </div>
            </div>

            <div class="card-content">
                <div class="front">
                    <strong>Front:</strong>
                    {#if card.cardType === 2}
                        {@html formatCloze(card.front)}
                    {:else}
                        {card.front}
                    {/if}
                </div>
                {#if card.back && card.cardType !== 2}
                    <div class="back">
                        <strong>Back:</strong>
                        {card.back}
                    </div>
                {/if}
            </div>

            {#if card.suggestedTags.length > 0}
                <div class="card-tags">
                    {#each card.suggestedTags as tag}
                        <span class="tag">{tag}</span>
                    {/each}
                </div>
            {/if}
        </div>
    {/each}
</div>

<style lang="scss">
    .btn-sm {
        padding: 0.25rem 0.5rem;
        font-size: 0.875rem;
        line-height: 1;
    }

    .btn-success {
        background-color: var(--flag-4);
        color: white;
        border: none;

        &:hover {
            opacity: 0.9;
        }
    }

    .btn-danger {
        background-color: var(--flag-1);
        color: white;
        border: none;

        &:hover {
            opacity: 0.9;
        }
    }

    :global(.cloze) {
        background-color: var(--accent);
        color: white;
        padding: 0.125rem 0.25rem;
        border-radius: 3px;
        font-weight: 500;
    }
</style>
