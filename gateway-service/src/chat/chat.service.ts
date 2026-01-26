import { Injectable, InternalServerErrorException } from '@nestjs/common';
import axios from 'axios';
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

@Injectable()
export class ChatService {
  private readonly PYTHON_API_URL =
    process.env.PYTHON_API_URL || 'http://localhost:8000/rag-chat';

  async getAiResponse(query: string, userId: string, sessionId?: string) {
    try {
      // 1. If no sessionId is provided, create a new Chat Session
      let currentSessionId = sessionId;
      if (!currentSessionId) {
        const newSession = await prisma.chatSession.create({
          data: {
            user_id: userId,
            title: query.substring(0, 30), // Use first 30 chars of query as title
          },
        });
        currentSessionId = newSession.id;
      }

      // 2. Get the AI Response from the Python Worker
      const pythonResponse = await axios.post(this.PYTHON_API_URL, {
        query: query,
        userId: userId,
      });

      const aiAnswer = pythonResponse.data.answer;
      const sources = pythonResponse.data.sources;

      // 3. Save the interaction to the database
      await prisma.chatMessage.create({
        data: {
          chat_session_id: currentSessionId,
          user_query: query,
          ai_response: aiAnswer,
          sources: sources, // Prisma handles JSON automatically
        },
      });

      // 4. Return the response AND the session ID to the user
      return {
        success: true,
        sessionId: currentSessionId, // Frontend needs this for the next question
        answer: aiAnswer,
        sources: sources,
      };
    } catch (error) {
      console.error('Python API Error:', error.message);
      throw new InternalServerErrorException(
        'Failed to connect to the AI Engine.',
      );
    }
  }
}
