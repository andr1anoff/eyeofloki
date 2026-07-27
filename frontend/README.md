# Eye of Loki frontend

Private, static Vite frontend for Vercel. Contest history, the discovery round
and the Railway connection stay in browser localStorage. Web discovery and LLM
verification are performed only by the separately deployed Railway service.

## Local run

```bash
npm install
npm run dev
```

## Vercel

Import the GitHub repository in Vercel and set **Root Directory** to
`frontend`. Vercel detects the checked-in Vite settings automatically.

After the first deployment, add the generated Vercel origin to Railway's
`ALLOWED_ORIGINS` variable. Use the exact production origin without a trailing
slash, then redeploy Railway.
