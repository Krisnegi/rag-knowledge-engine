import { Controller, Post, Body, HttpCode, HttpStatus } from '@nestjs/common';
import { AuthService } from './auth.service';

@Controller('auth')
export class AuthController {
  constructor(private readonly authService: AuthService) {}

  @Post('signup')
  async signUp(@Body('email') email: string, @Body('password') pass: string) {
    return this.authService.signUp(email, pass);
  }

  @HttpCode(HttpStatus.OK) // Returns 200 OK instead of 201 Created
  @Post('login')
  async login(@Body('email') email: string, @Body('password') pass: string) {
    return this.authService.login(email, pass);
  }
}
