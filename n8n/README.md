# n8n Workflow Setup

This folder contains an importable n8n workflow that mirrors the FastAPI backend contract.

## Import

1. Open n8n.
2. Choose **Import from file**.
3. Select `n8n/startup-validator-workflow.json`.
4. Add credentials or environment variables:
   - `GROQ_API_KEY`
   - `TAVILY_API_KEY`
5. Activate the workflow and copy the production webhook URL.

## Frontend switch

In `frontend/index.html`, change the config at the top of the script if you want the UI to call n8n instead of FastAPI:

```js
window.STARTUP_VALIDATOR_API_URL = "https://your-n8n-instance.com/webhook/startup-validator";
window.STARTUP_VALIDATOR_BACKEND_LABEL = "n8n";
```

The webhook response must keep the same shape as `POST /validate`:

```json
{
  "execution_mode": "sequential",
  "execution_time_s": 12.4,
  "specialist_reports": {},
  "conflicts_detected": [],
  "final_evaluation": {}
}
```

## Notes

- The workflow uses Groq for LLM generation and Tavily for market search.
- The viability branch uses deterministic JavaScript calculations inside Code nodes.
- If your n8n instance does not allow environment variables inside expressions, replace the credential expressions with n8n credentials before activation.

