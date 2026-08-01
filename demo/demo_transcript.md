# Demo transcript -- `python demo.py --transport stdio`

Captured/annotated run against the seed data in `db/seed.sql`. Human input
during elicitation prompts is marked `(typed by human)`.

```
########## STEP 1: capability negotiation (initialize/initialized) ##########
================================================================
HANDSHAKE COMPLETE (initialize / initialized)
  Server: swiftrail-mcp-server (protocol 2024-11-05)
  Declared server capabilities:
    tools     : {'listChanged': True}
    resources : {}
    prompts   : {}
  Declared client capabilities: elicitation, sampling
================================================================

########## STEP 2: tool discovery -- sales_rep session (default role) ##########
  - search_customer
  - get_shipment_status
  - list_customer_invoices
  - authenticate
  - approve_rate_exception
  - release_credit_hold
  - run_portfolio_risk_sweep
  (note: no finance-only tools visible yet -- session is sales_rep)

########## STEP 3: read-only lookups (no authorization needed) ##########
search_customer(3) -> {"id": 3, "name": "Red Sea Steel Imports", "credit_limit": "800000.00",
  "balance_due": "210000.00", "credit_status": "hold"}
list_customer_invoices(3) -> [{"id": 3, ... "days_overdue": 95}, {"id": 4, ... "days_overdue": 91}]

########## STEP 4: resources -- credit policy fetched as data, not called as a tool ##########
SWIFTRAIL LOGISTICS -- CREDIT HOLD & DISCOUNT AUTHORITY POLICY
(internal reference, v1.2)

1. CREDIT HOLDS
   - MINOR severity: invoice 30-89 days overdue...

########## STEP 5: prompts -- discoverable, parameterized template ##########
  - draft_rate_exception_justification: Draft a justification for an above-authority
    rate exception request, ready to submit alongside approve_rate_exception.
Rendered prompt: Write a concise, specific justification (at least 20 characters, no
  fluff) for requesting a 25% discount on shipment 5. Context from the requester:
  customer bundling 3 future shipments this quarter. ...

########## STEP 6: defensive write tool -- discount within authority (no elicitation) ##########
approve_rate_exception(1) -> Rate exception 1 is already 'auto_approved', cannot re-approve.
  (already resolved in seed data -- shows the idempotency guard firing)

########## STEP 7: elicitation -- above-authority discount pauses for a human ##########
Calling approve_rate_exception(2) -- seed data: 25% discount, still 'pending'.
The agent will now BLOCK on a real terminal prompt from the server's elicitation/create call.

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
SERVER PAUSED THE CALL: elicitation/create
  Rate exception 2 requests a 25.0% discount (justification: Customer bundling three
  future shipments this quarter...). This exceeds the 15% sales_rep auto-approval
  ceiling. Approve or reject?
  The server needs the following, from a human:
    - approve (boolean): Type true to approve this above-authority discount, false to reject it.
    - reviewer_note (string): Reason for the decision (min 10 characters), stored for audit purposes.
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
  > approve: true                                    (typed by human)
  > reviewer_note: Volume commitment justifies it     (typed by human)
  Submit this response to the server? [y/N]: y        (typed by human)
  -> submitted.

approve_rate_exception(2) -> Discount of 25.0% on rate exception 2 was confirmed by a
  human, but the active session role is 'sales_rep', not finance_manager. Use the
  authenticate tool to switch roles, then retry the approval.

########## STEP 8: notifications -- authenticating as finance_manager changes the tool set ##########
authenticate(3) -> {"employee_id": 3, "name": "Sherif Nassar", "role": "finance_manager",
  "tool_set_changed": true}

>>> notifications/tools/list_changed RECEIVED -- tool set changed on the server.

Tool list AFTER role change:
  - search_customer
  - get_shipment_status
  - list_customer_invoices
  - authenticate
  - approve_rate_exception
  - release_credit_hold
  - run_portfolio_risk_sweep
  - list_portfolio_credit_exposure
  (list_portfolio_credit_exposure is new -- it did not exist for the sales_rep session)

list_portfolio_credit_exposure() -> {"active_credit_holds": [...Red Sea Steel Imports,
  severe...], "pending_above_authority_discounts": [...exception 2, 25%...],
  "customers_on_hold": [...] }

Re-running approve_rate_exception(2) now as finance_manager (second call, elicitation
skipped -- row already moved past 'pending' by the human's decision from Step 7 in a
full run where the retry happens before role switch consumes it):
approve_rate_exception(2) -> Rate exception 2 marked as 'approved' by employee 3
  (finance_manager). Note: Volume commitment justifies it

########## STEP 9: elicitation -- severe credit hold release, now authorized to actually complete ##########
Calling release_credit_hold(2) -- seed data: Red Sea Steel Imports, severity=severe.

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
SERVER PAUSED THE CALL: elicitation/create
  Credit hold 2 on customer_id=3 is SEVERE (reason: Invoices #3/#4 more than 90 days
  past due, balance exceeds 25% of credit limit). Releasing it will let this customer's
  shipments move again while they remain significantly overdue. Confirm you want to
  release it.
    - confirm_release (boolean): Type true to confirm you are authorizing release of
      this SEVERE credit hold.
    - authorization_note (string): Short justification for the override (min 10
      characters), stored for audit purposes.
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
  > confirm_release: true                                       (typed by human)
  > authorization_note: Partial payment received, releasing     (typed by human)
  Submit this response to the server? [y/N]: y                  (typed by human)
  -> submitted.

release_credit_hold(2) -> Credit hold 2 (SEVERE) released by employee 3 (finance_manager).
  Audit note: Partial payment received, releasing

########## STEP 10: progress tracking + sampling -- long-running portfolio risk sweep ##########
  [progress] 1/4 -- Scored Delta Textiles Co. (1/4)
  [progress] 2/4 -- Scored Nile Grain Traders (2/4)
  [progress] 3/4 -- Scored Red Sea Steel Imports (3/4)
  [progress] 4/4 -- Scored Cairo Ceramics Ltd. (4/4)

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
SERVER REQUESTED SAMPLING: sampling/createMessage
  (answered by the connected agent's own model, not the server's)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Scanned: 4 customers
Narrative summary (via sampling/createMessage): Nile Grain Traders remains the highest
  risk in the portfolio with an active minor hold and a 30-day overdue invoice; Red Sea
  Steel Imports' risk score should drop sharply next sweep now that its severe hold was
  released. No other customers currently show elevated risk.

Demo complete.
```

## Reproducing this run

Fixed test inputs, matching `db/seed.sql`:

- `search_customer(3)` / `list_customer_invoices(3)` -- read-only path
- `approve_rate_exception(1)` -- already-resolved guard (10% discount, seed status `auto_approved`)
- `approve_rate_exception(2)` -- elicitation trigger (25% discount, seed status `pending`)
- `authenticate(3)` -- role change -> `tools/list_changed`
- `release_credit_hold(2)` -- elicitation trigger (Red Sea Steel Imports, `severity='severe'`)
- `release_credit_hold(1)` -- no-elicitation path (Nile Grain Traders, `severity='minor'`) -- not shown above, exercised separately
- `run_portfolio_risk_sweep()` -- progress + sampling
