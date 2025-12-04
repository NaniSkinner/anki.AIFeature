<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<script lang="ts">
    import { createEventDispatcher } from "svelte";

    export let title: string;
    export let showNewButton = false;

    const dispatch = createEventDispatcher<{ new: void }>();
</script>

<header class="sticky-header">
    <h1>{title}</h1>
    {#if showNewButton}
        <button class="btn" on:click={() => dispatch("new")}>New Session</button>
    {/if}
</header>

<style lang="scss">
    .sticky-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem 1rem;
        background: var(--canvas-elevated);
        border-bottom: 1px solid var(--border);
        position: sticky;
        top: 0;
        z-index: 100;

        h1 {
            margin: 0;
            font-size: 1.25rem;
            font-weight: 600;
        }
    }
</style>
