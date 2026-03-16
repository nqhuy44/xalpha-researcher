import { getSession } from '@/lib/auth';
import { NextResponse } from 'next/server';

export async function GET() {
  const session = await getSession();
  if (session) {
    return NextResponse.json({ authenticated: true, user: session.sub });
  }
  return NextResponse.json({ authenticated: false }, { status: 401 });
}
