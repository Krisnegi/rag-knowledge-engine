import {
  Controller,
  Post,
  Body,
  BadRequestException,
  UseGuards,
  Request,
} from '@nestjs/common';
import { ChatService } from './chat.service';
import { AuthGuard } from '@nestjs/passport';

@Controller('chat')
export class ChatController {
  constructor(private readonly chatService: ChatService) {}

  @UseGuards(AuthGuard('jwt')) // <-- SECURE THIS ROUTE
  @Post()
  async chatWithAI(
    @Request() req,
    @Body('query') query: string,
    @Body('sessionId') sessionId?: string, // <-- Optional: If provided, continue this chat
  ) {
    if (!query) {
      throw new BadRequestException('Query is required.');
    }

    // req.user.sub is available because of the validate() function in the strategy!
    console.log(`User ${req.user.sub} is asking: ${query}`);

    return this.chatService.getAiResponse(query, req.user.sub, sessionId);
  }
}
