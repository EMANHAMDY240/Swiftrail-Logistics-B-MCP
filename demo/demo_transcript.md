# Demo transcript -- `python demo.py --transport stdio`

Real, captured run against the seed data in `db/seed.sql`. Human input
during elicitation prompts is marked `(typed by human)`.

```
########## STEP 1: capability negotiation (initialize/initialized) ##########
================================================================
HANDSHAKE COMPLETE (initialize / initialized)
  Server: swiftrail-mcp-server (protocol 2025-11-25)
  Declared server capabilities:
    tools     : list_changed=False
    resources : subscribe=False list_changed=False
    prompts   : list_changed=False
  Declared client capabilities: elicitation, sampling
================================================================

########## STEP 2: tool discovery -- sales_rep session (default role) ##########
  - search_customer
  - get_shipment_status
  - list_customer_invoices
  - approve_rate_exception
  - release_credit_hold
  - run_portfolio_risk_sweep
  - authenticate
  (note: no finance-only tools visible yet -- session is sales_rep)

########## STEP 3: read-only lookups (no authorization needed) ##########
search_customer(3) -> {"id": 3, "name": "Red Sea Steel Imports", "credit_limit": "800000.00",
  "balance_due": "210000.00", "credit_status": "hold"}
list_customer_invoices(3) -> [{"id": 3, ..."days_overdue": 95}, {"id": 4, ..."days_overdue": 91}]

########## STEP 4: resources -- credit policy fetched as data, not called as a tool ##########
SWIFTRAIL LOGISTICS -- CREDIT HOLD & DISCOUNT AUTHORITY POLICY
(internal reference, v1.2)

1. CREDIT HOLDS
   - MINOR severity: invoice 30-89 days overdue. A sales_rep session
     may release these directly.
   - SEVERE severity: invoice 90+ days overdue, OR overdue balance
     exceeds 25% of the customer's credit limit. Release always
     pauses for explicit human confirmation, and can only be...

########## STEP 5: prompts -- discoverable, parameterized template ##########
  - draft_rate_exception_justification: Draft a justification for an above-authority
    rate exception request, ready to submit alongside approve_rate_exception.
Rendered prompt: Write a concise, specific justification (at least 20 characters, no
  fluff) for requesting a 25% discount on shipment 5. Context from the requester:
  customer bundling 3 future shipments this quarter.

########## STEP 6: defensive write tool -- discount within authority (no elicitation) ##########
approve_rate_exception(1) -> Rate exception 1 is already 'auto_approved', cannot re-approve.
  (already resolved in seed data -- shows the idempotency guard firing)

########## STEP 7: elicitation -- above-authority discount pauses for a human ##########
Calling approve_rate_exception(2) -- seed data: 25% discount, still 'pending'.
The agent will now BLOCK on a real terminal prompt from the server's elicitation/create call.

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
SERVER PAUSED THE CALL: elicitation/create
  Rate exception 2 requests a 25.0% discount (justification: Customer bundling three
  future shipments this quarter; requesting deeper discount to secure the volume
  commitment.). This exceeds the 15% sales_rep auto-approval ceiling. Approve or reject?
  The server needs the following, from a human:
    - approve (boolean): Type true to approve this above-authority discount, false to reject it.
    - reviewer_note (string): Reason for the decision (min 10 characters), stored for audit purposes.
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
  > approve: true                                          (typed by human)
  > reviewer_note: Volume commitment justifies the discount (typed by human)
  Submit this response to the server? [y/N]: y              (typed by human)
  -> submitted.

approve_rate_exception(2) -> Discount of 25.0% on rate exception 2 was confirmed by a
  human, but the active session role is 'sales_rep', not finance_manager. Use the
  authenticate tool to switch roles, then retry the approval.

########## STEP 8: notifications -- authenticating as finance_manager changes the tool set ##########
authenticate(3) -> {"employee_id": 3, "name": "Sherif Nassar", "role": "finance_manager",
  "tool_set_changed": true}

list_portfolio_credit_exposure() -> {"active_credit_holds": [{"id": 1, "customer_id": 2,
  "reason": "Invoice #2 30 days past due", "severity": "minor", "status": "active",
  "customer_name": "Nile Grain Traders"}, {"id": 2, "customer_id": 3, "reason":
  "Invoices #3/#4 more than 90 days past due, balance exceeds 25% of credit limit",
  "severity": "severe", "status": "active", ...}], ...}

########## STEP 9: elicitation -- severe credit hold release, now authorized to actually complete ##########
Calling release_credit_hold(2) -- seed data: Red Sea Steel Imports, severity=severe.

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
SERVER PAUSED THE CALL: elicitation/create
  Credit hold 2 on customer_id=3 is SEVERE (reason: Invoices #3/#4 more than 90 days
  past due, balance exceeds 25% of credit limit). Releasing it will let this customer's
  shipments move again while they remain significantly overdue. Confirm you want to
  release it.
    - confirm_release (boolean): Type true to confirm you are authorizing release of
      this SEVERE credit hold.
    - authorization_note (string): Short justification for the override (min 10
      characters), stored for audit purposes.
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
  > confirm_release: true                                       (typed by human)
  > authorization_note: Partial payment received, releasing hold (typed by human)
  Submit this response to the server? [y/N]: y                  (typed by human)
  -> submitted.

release_credit_hold(2) -> Credit hold 2 (SEVERE) released by employee 3 (finance_manager).
  Audit note: Partial payment received, releasing hold

########## STEP 10: progress tracking + sampling -- long-running portfolio risk sweep ##########
  [progress] 1.0/4.0 -- Scored Delta Textiles Co. (1/4)
  [progress] 2.0/4.0 -- Scored Nile Grain Traders (2/4)
  [progress] 3.0/4.0 -- Scored Red Sea Steel Imports (3/4)
  [progress] 4.0/4.0 -- Scored Cairo Ceramics Ltd. (4/4)

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
SERVER REQUESTED SAMPLING: sampling/createMessage
  (answered by the connected agent's own model, not the server's)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Scanned: 4 customers
Narrative summary (via sampling/createMessage): [offline demo mode -- set
  ANTHROPIC_API_KEY for a real completion] Summary based on prompt: Write a 2-3
  sentence portfolio risk summary for a finance manager based on this data: ...

Demo complete.
```

## Reproducing this run

Fixed test inputs, matching `db/seed.sql`:

- `search_customer(3)` / `list_customer_invoices(3)` -- read-only path
- `approve_rate_exception(1)` -- already-resolved guard (10% discount, seed status `auto_approved`)
- `approve_rate_exception(2)` -- elicitation trigger (25% discount, seed status `pending`)
- `authenticate(3)` -- role change -> `tools/list_changed`
- `release_credit_hold(2)` -- elicitation trigger (Red Sea Steel Imports, `severity='severe'`)
- `release_credit_hold(1)` -- no-elicitation path (Nile Grain Traders, `severity='minor'`) -- exercised separately
- `run_portfolio_risk_sweep()` -- progress + sampling

Set `ANTHROPIC_API_KEY` in the environment before running the demo to get a
real sampling completion in Step 10 instead of the offline stub text shown
above.
