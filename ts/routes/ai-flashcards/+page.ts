// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import { getDeckNames, loadSession } from "@generated/backend";

import type { PageLoad } from "./$types";

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

export const load = (async () => {
    const [decks, sessionResponse] = await Promise.all([
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

    return { decks, session };
}) satisfies PageLoad;
