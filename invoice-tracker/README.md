# Invoice Tracker

A Next.js 16 application for tracking and analyzing invoices/receipts.

## Features

- **Authentication**: Secure login/signup via Supabase.
- **Invoice Upload**: Drag & drop upload for images/PDFs.
- **Automated Processing**: Integration with N8N webhooks.
- **Analytics**: Real-time charts and spending summaries.
- **Dark Mode**: Fully supported dark/light themes.

## Tech Stack

- Next.js 16 (App Router)
- Supabase (Auth, Database, Storage)
- Tailwind CSS & shadcn/ui
- Recharts
- TypeScript

## Setup

1. **Clone the repository**
2. **Install dependencies**:
   ```bash
   npm install
   ```
3. **Configure Environment Variables**:
   Create `.env.local` with:
   ```
   NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
   N8N_WEBHOOK_URL=your_n8n_webhook_url
   ```
4. **Setup Database**:
   Run the SQL found in `supabase/schema.sql` in your Supabase SQL Editor.
   Create a storage bucket named `invoices`.

5. **Run Development Server**:
   ```bash
   npm run dev
   ```

## Folder Structure

- `src/app`: Pages and API routes.
- `src/components`: UI components and feature-specific blocks.
- `src/lib`: Utilities and helper functions.
- `src/proxy.ts`: Middleware proxy for protected routes.
