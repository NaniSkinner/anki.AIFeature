<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<script lang="ts">
    import { pageTheme } from "$lib/sveltelib/theme";

    const rtl: boolean = window.getComputedStyle(document.body).direction == "rtl";

    export let id: string | undefined = undefined;
    let className: string = "";
    export { className as class };

    export let title: string;
</script>

<div
    {id}
    class="container {className}"
    class:light={!$pageTheme.isDark}
    class:dark={$pageTheme.isDark}
    class:rtl
    style:--gutter-block="2px"
    style:--container-margin="0"
>
    <div class="position-relative">
        <h1>
            {title}
        </h1>
        <div class="help-badge position-absolute" class:rtl>
            <slot name="tooltip" />
        </div>
    </div>
    <slot />
</div>

<style lang="scss">
    @use "../sass/elevation" as *;
    .container {
        width: 100%;
        background: var(--canvas-elevated);
        border: none;
        border-radius: var(--border-radius-medium);

        &.light {
            @include soft-elevation(2);
        }
        &.dark {
            @include soft-elevation-dark(2);
        }

        padding: var(--spacing-lg) var(--spacing-xl);
        &.rtl {
            padding: var(--spacing-lg) var(--spacing-xl);
        }
        page-break-inside: avoid;

        transition: box-shadow var(--transition) var(--easing);
        &:hover {
            &.light {
                @include soft-elevation(3);
            }
            &.dark {
                @include soft-elevation-dark(3);
            }
        }
    }
    h1 {
        border-bottom: none;
        padding-bottom: var(--spacing-md);
        margin-bottom: var(--spacing-sm);
        font-weight: 600;
        font-size: 1.1rem;
    }
    .help-badge {
        right: 0;
        top: 0;
        color: var(--fg-subtle);
        &.rtl {
            right: unset;
            left: 0;
        }
    }

    :global(.night-mode) .help-badge {
        color: var(--fg);
    }
</style>
