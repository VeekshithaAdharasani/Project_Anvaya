import { API_BASE_URL } from './apiConfig';

export interface ChatRequestPayload {
    session_id: string;
    message: string;
}

export interface ChatResponse {
    response: string;
}

export async function sendChatMessage(sessionId: string, message: string): Promise<ChatResponse> {
    const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ session_id: sessionId, message } satisfies ChatRequestPayload),
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || 'Failed to send chat message.');
    }

    return response.json() as Promise<ChatResponse>;
}
