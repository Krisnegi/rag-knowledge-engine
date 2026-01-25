import { Controller, Post, Body, UseGuards, Request } from '@nestjs/common';
import { IngestionService } from './ingestion.service';
import { IngestUrlDto } from './dto/ingest-url.dto';
import { AuthGuard } from '@nestjs/passport';

@Controller('ingestion')
export class IngestionController {
  constructor(private readonly ingestionService: IngestionService) {}

  @UseGuards(AuthGuard('jwt')) // <-- SECURE THIS ROUTE
  @Post()
  async ingest(@Request() req, @Body() dto: IngestUrlDto) {
    const userId = req.user.sub; // Extract User ID from the JWT

    return this.ingestionService.addScrapingJob(dto.url, userId);
  }
}
