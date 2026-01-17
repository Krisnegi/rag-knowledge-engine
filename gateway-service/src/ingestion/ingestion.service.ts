// src/ingestion/ingestion.service.ts
import { Injectable, Inject } from '@nestjs/common';
import Redis from 'ioredis';
import { PrismaService } from '../prisma.service';

@Injectable()
export class IngestionService {
  constructor(
    @Inject('REDIS_CLIENT') private readonly redis: Redis,
    private readonly prisma: PrismaService,
  ) {}

  async addScrapingJob(url: string, userId: string) {
    // 1. Create the "Pending" record in Postgres first (Source of Truth)
    const document = await this.prisma.document.create({
      data: {
        source_url: url,
        user_id: userId,
        status: 'PENDING',
      },
    });

    // 2. Prepare the Job Payload
    // We attach the document.id so the Python worker knows which DB row to update later!
    const jobData = {
      jobId: document.id, // This is our UUID
      url: document.source_url,
      userId: document.user_id,
    };

    // 3. Push to Redis
    await this.redis.lpush('scraping_queue', JSON.stringify(jobData));

    // 4. Return the ID to the user
    return {
      jobId: document.id,
      status: 'PENDING',
      message: 'Job successfully queued',
    };
  }
}
