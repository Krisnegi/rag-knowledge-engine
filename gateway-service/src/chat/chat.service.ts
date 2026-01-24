import { Injectable, InternalServerErrorException } from '@nestjs/common';
import axios from 'axios';

@Injectable()
export class ChatService {
  private readonly PYTHON_API_URL = 'http://localhost:8000/rag-chat';

  async getAiResponse(query: string) {
    try {
      const pythonResponse = await axios.post(this.PYTHON_API_URL, {
        query: query,
      });

      return {
        success: true,
        answer: pythonResponse.data.answer,
        sources: pythonResponse.data.sources,
      };
    } catch (error) {
      console.error('Python API Error:', error.message);
      throw new InternalServerErrorException(
        'Failed to connect to the AI Engine.',
      );
    }
  }
}
