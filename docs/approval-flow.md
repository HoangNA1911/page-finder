# Payment Approval Flow

## Purpose

The approval flow controls when a payment request can move from draft to execution.

## Main Rules

- Payments below 100 million VND require one approver from the finance manager group.
- Payments from 100 million VND to 500 million VND require two approvers: finance manager and product owner.
- Payments above 500 million VND require finance director approval before execution.

## Operational Notes

- The request must include merchant ID, business reason, and evidence links.
- If the approver rejects the request, the system returns the request to `NEEDS_REVISION`.
- If no approver responds within 24 hours, the workflow sends a reminder event.

## Risks

- Missing evidence links causes manual review delay.
- Requests with duplicate merchant IDs can be blocked by fraud review.

## Escalation

- Finance operations handles normal approval delays.
- The payment core on-call team handles workflow engine incidents.
