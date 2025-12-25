import { createClient } from '@/supabase/server'
import { NextResponse } from 'next/server'

export async function POST(request: Request) {
  try {
    const { imageUrl, userId } = await request.json()
    
    if (!imageUrl || !userId) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 })
    }

    // Call N8N Webhook
    const n8nWebhookUrl = process.env.N8N_WEBHOOK_URL
    if (!n8nWebhookUrl) {
        return NextResponse.json({ error: 'N8N Webhook URL not configured' }, { status: 500 })
    }

    const n8nResponse = await fetch(n8nWebhookUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            imageUrl,
            userId,
            timestamp: new Date().toISOString()
        })
    })

    if (!n8nResponse.ok) {
        throw new Error(`N8N Webhook Error: ${n8nResponse.statusText}`)
    }

    const n8nDataRaw = await n8nResponse.json()
    
    // Normalize N8N data (Handle array or object wrapper)
    // The user receives: [{"Date": "...", "Company": "...", "Amount": 73.05, ...}]
    let invoiceData: any = {}

    if (Array.isArray(n8nDataRaw) && n8nDataRaw.length > 0) {
        invoiceData = n8nDataRaw[0]
    } else if (n8nDataRaw.data) {
        invoiceData = n8nDataRaw.data
    } else {
        invoiceData = n8nDataRaw
    }
    
    // Map fields (handling Case Sensitivity and defaults)
    const company_name = invoiceData.company_name || invoiceData.Company || 'Unknown Company'
    
    // Handle Amount (remove '=' if present, ensure numeric)
    let amountRaw = invoiceData.amount || invoiceData.Amount || 0
    if (typeof amountRaw === 'string') {
        amountRaw = amountRaw.replace('=', '').trim()
    }
    const amount = parseFloat(amountRaw)
    
    const currency = invoiceData.currency || invoiceData.Currency || 'USD'
    const date = invoiceData.date || invoiceData.Date || new Date().toISOString().split('T')[0]
    const category = invoiceData.category || invoiceData.Category || 'Uncategorized'
    
    // Processed At
    const processed_at = invoiceData.processed_at || invoiceData['Processed At'] || new Date().toISOString()

    // Insert the processed data into Supabase
    const supabase = await createClient()
    const { data, error } = await supabase.from('invoices').insert({
        user_id: userId,
        company_name,
        amount,
        currency,
        date,
        category,
        image_url: imageUrl, // Always use the uploaded image URL as the source
        processed_at
    }).select().single()

    if (error) {
        console.error("DB Insert Error:", error)
        return NextResponse.json({ error: error.message }, { status: 500 })
    }

    return NextResponse.json({ success: true, data })

  } catch (error: any) {
    console.error("Process Invoice Error:", error)
    return NextResponse.json({ error: error.message }, { status: 500 })
  }
}
