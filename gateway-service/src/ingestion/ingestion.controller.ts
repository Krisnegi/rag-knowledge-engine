import { Controller, Post, Body } from '@nestjs/common';
import { IngestionService } from './ingestion.service';
import { IngestUrlDto } from './dto/ingest-url.dto';

@Controller('ingestion')
export class IngestionController {
  constructor(private readonly ingestionService: IngestionService) {}

  @Post()
  async ingest(@Body() dto: IngestUrlDto) {
    // Mock user ID for now (Phase 3 will add real Auth)
    const mockUserId = 'user-123';
    return this.ingestionService.addScrapingJob(dto.url, mockUserId);
  }
}
