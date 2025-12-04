// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import "./ai-flashcards-base.scss";

import { getDeckNames, loadSession } from "@generated/backend";
import { ModuleName, setupI18n } from "@tslib/i18n";
import { checkNightMode } from "@tslib/nightmode";

import { modalsKey } from "$lib/components/context-keys";

import AIFlashcardsPage from "./AIFlashcardsPage.svelte";

// Simple session interface
interface SimpleSession {
    hasSession: boolean;
    cards: Array<{
        id: string;
        cardType: number;
        front: string;
        back: string;
        suggestedTags: string[];
        status: number;
    }>;
    sourceName: string;
    sourceText: string;
}

const i18n = setupI18n({
    modules: [
        ModuleName.ACTIONS,
        ModuleName.IMPORTING,
        ModuleName.ADDING,
        ModuleName.EDITING,
    ],
});

export async function setupAIFlashcardsPage(): Promise<AIFlashcardsPage> {
    const [_, decks, sessionResponse] = await Promise.all([
        i18n,
        getDeckNames({
            skipEmptyDefault: false,
            includeFiltered: false,
        }),
        loadSession({}, { alertOnError: false }).catch(() => null),
    ]);

    // Convert to simple session format
    const session: SimpleSession = sessionResponse
        ? {
            hasSession: sessionResponse.hasSession,
            cards: sessionResponse.cards.map(c => ({
                id: c.id,
                cardType: c.cardType,
                front: c.front,
                back: c.back,
                suggestedTags: [...c.suggestedTags],
                status: c.status,
            })),
            sourceName: sessionResponse.sourceName,
            sourceText: sessionResponse.sourceText,
        }
        : {
            hasSession: false,
            cards: [],
            sourceName: "",
            sourceText: "",
        };

    const context = new Map();
    context.set(modalsKey, new Map());
    checkNightMode();

    return new AIFlashcardsPage({
        target: document.body,
        props: {
            decks,
            session,
        },
        context,
    });
}

// For testing: http://localhost:40000/_anki/pages/ai-flashcards.html#test
if (window.location.hash.startsWith("#test")) {
    setupAIFlashcardsPage();
}
