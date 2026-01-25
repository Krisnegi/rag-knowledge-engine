import { ExtractJwt, Strategy } from 'passport-jwt';
import { PassportStrategy } from '@nestjs/passport';
import { Injectable } from '@nestjs/common';

@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy) {
  constructor() {
    super({
      // 1. Automatically extract token from the Bearer header
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      ignoreExpiration: false,
      // 2. The secret key to verify the token
      secretOrKey: process.env.JWT_SECRET || 'super-secret-key',
    });
  }

  // 3. If the token is valid, Passport calls this function with the decoded data
  async validate(payload: any) {
    // This return value automatically gets attached to `req.user`!
    return { sub: payload.sub, email: payload.email };
  }
}
