// src/ingestion/ingestion.module.ts
import { Module } from '@nestjs/common';
import { IngestionController } from './ingestion.controller';
import { IngestionService } from './ingestion.service';
import { PrismaService } from '../prisma.service';
import Redis from 'ioredis';

@Module({
  controllers: [IngestionController],
  providers: [
    IngestionService,
    PrismaService,
    {
      provide: 'REDIS_CLIENT',
      useFactory: () => {
        return new Redis({
          host: 'localhost', // Use env var in production
          port: 6379,
        });
      },
    },
  ],
})
export class IngestionModule {}
