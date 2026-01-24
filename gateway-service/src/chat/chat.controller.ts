import { Controller, Post, Body, BadRequestException } from '@nestjs/common';
import { ChatService } from './chat.service';

@Controller('chat')
export class ChatController {
  constructor(private readonly chatService: ChatService) {}

  @Post()
  async chatWithAI(@Body('query') query: string) {
    if (!query) {
      throw new BadRequestException('Query is required.');
    }
    return this.chatService.getAiResponse(query);
  }
}
