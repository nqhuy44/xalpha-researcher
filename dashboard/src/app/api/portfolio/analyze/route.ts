import { getSession, encrypt } from '@/lib/auth';
import { NextResponse } from 'next/server';

const PYTHON_API_URL = process.env.PYTHON_API_URL || 'http://localhost:8000';

export async function POST(request: Request) {
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    const { symbol } = await request.json();
    if (!symbol) {
      return NextResponse.json({ error: 'Symbol is required' }, { status: 400 });
    }

    const token = await encrypt({ sub: session.sub });
    
    // Proxy the request to the Python AI service
    const response = await fetch(`${PYTHON_API_URL}/api/v1/portfolio/${symbol.toUpperCase()}/analyze`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (!response.ok) {
      const error = await response.json();
      return NextResponse.json(error, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error('Analysis Trigger Proxy Error:', error.message);
    return NextResponse.json({ 
      error: 'Analysis trigger failed', 
      details: error.message 
    }, { status: 500 });
  }
}
