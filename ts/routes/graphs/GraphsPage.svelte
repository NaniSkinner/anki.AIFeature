<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<script lang="ts">
    import { bridgeCommand } from "@tslib/bridgecommand";
    import type { Component } from "svelte";
    import { writable } from "svelte/store";

    import { pageTheme } from "$lib/sveltelib/theme";

    import RangeBox from "./RangeBox.svelte";
    import WithGraphData from "./WithGraphData.svelte";

    export let initialSearch: string;
    export let initialDays: number;

    const search = writable(initialSearch);
    const days = writable(initialDays);

    export let graphs: Component<any>[];
    /** See RangeBox */
    export let controller: Component<any> | null = RangeBox;

    function browserSearch(event: CustomEvent) {
        bridgeCommand(`browserSearch: ${$search} ${event.detail.query}`);
    }
</script>

<WithGraphData {search} {days} let:sourceData let:loading let:prefs let:revlogRange>
    {#if controller}
        <svelte:component this={controller} {search} {days} {loading} />
    {/if}

    <div class="graphs-container">
        {#if sourceData && revlogRange}
            {#each graphs as graph}
                <svelte:component
                    this={graph}
                    {sourceData}
                    {prefs}
                    {revlogRange}
                    nightMode={$pageTheme.isDark}
                    on:search={browserSearch}
                />
            {/each}
        {/if}
    </div>
    <div class="spacer"></div>
</WithGraphData>

<style lang="scss">
    .graphs-container {
        display: grid;
        gap: var(--spacing-lg);
        grid-template-columns: repeat(3, minmax(0, 1fr));
        // required on Safari to stretch whole width
        width: calc(100vw - var(--spacing-xl) * 2);
        margin-left: var(--spacing-xl);
        margin-right: var(--spacing-xl);
        padding: var(--spacing-md) 0;

        @media only screen and (max-width: 600px) {
            width: calc(100vw - var(--spacing-md));
            margin-left: var(--spacing-sm);
            margin-right: var(--spacing-sm);
            gap: var(--spacing-md);
        }

        @media only screen and (max-width: 1400px) {
            grid-template-columns: 1fr 1fr;
        }
        @media only screen and (max-width: 1200px) {
            grid-template-columns: 1fr;
        }
        @media only screen and (max-width: 600px) {
            font-size: 12px;
        }

        @media only print {
            // grid layout does not honor page-break-inside
            display: block;
            margin-top: 3em;
        }
    }

    .spacer {
        height: var(--spacing-xl);
    }
</style>
