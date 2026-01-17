// src/ingestion/dto/ingest-url.dto.ts
import { IsUrl, IsString, IsNotEmpty } from 'class-validator';

export class IngestUrlDto {
  @IsString()
  @IsNotEmpty()
  @IsUrl()
  url: string;
}
