-- Finance RLS: tenant isolation. Production app role must not own these tables
-- and must not have BYPASSRLS. Session vars set inside the write transaction.

ALTER TABLE finance_settings ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_settings_isolation ON finance_settings;
CREATE POLICY finance_settings_isolation ON finance_settings
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_role ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_role_isolation ON finance_role;
CREATE POLICY finance_role_isolation ON finance_role
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_grant ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_grant_isolation ON finance_grant;
CREATE POLICY finance_grant_isolation ON finance_grant
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_account ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_account_isolation ON finance_account;
CREATE POLICY finance_account_isolation ON finance_account
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_document_sequence ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_sequence_isolation ON finance_document_sequence;
CREATE POLICY finance_sequence_isolation ON finance_document_sequence
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_period_lock ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_period_isolation ON finance_period_lock;
CREATE POLICY finance_period_isolation ON finance_period_lock
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_journal ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_journal_isolation ON finance_journal;
CREATE POLICY finance_journal_isolation ON finance_journal
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_journal_line ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_journal_line_isolation ON finance_journal_line;
CREATE POLICY finance_journal_line_isolation ON finance_journal_line
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_idempotency ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_idempotency_isolation ON finance_idempotency;
CREATE POLICY finance_idempotency_isolation ON finance_idempotency
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_audit_event ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_audit_isolation ON finance_audit_event;
CREATE POLICY finance_audit_isolation ON finance_audit_event
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_contact ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_contact_isolation ON finance_contact;
CREATE POLICY finance_contact_isolation ON finance_contact
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_payment_term ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_payment_term_isolation ON finance_payment_term;
CREATE POLICY finance_payment_term_isolation ON finance_payment_term
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_tax_rate ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_tax_rate_isolation ON finance_tax_rate;
CREATE POLICY finance_tax_rate_isolation ON finance_tax_rate
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_exchange_rate ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_exchange_rate_isolation ON finance_exchange_rate;
CREATE POLICY finance_exchange_rate_isolation ON finance_exchange_rate
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_item ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_item_isolation ON finance_item;
CREATE POLICY finance_item_isolation ON finance_item
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_quote ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_quote_isolation ON finance_quote;
CREATE POLICY finance_quote_isolation ON finance_quote
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_quote_line ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_quote_line_isolation ON finance_quote_line;
CREATE POLICY finance_quote_line_isolation ON finance_quote_line
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_invoice ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_invoice_isolation ON finance_invoice;
CREATE POLICY finance_invoice_isolation ON finance_invoice
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_invoice_line ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_invoice_line_isolation ON finance_invoice_line;
CREATE POLICY finance_invoice_line_isolation ON finance_invoice_line
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_credit_note ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_credit_note_isolation ON finance_credit_note;
CREATE POLICY finance_credit_note_isolation ON finance_credit_note
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_credit_note_line ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_credit_note_line_isolation ON finance_credit_note_line;
CREATE POLICY finance_credit_note_line_isolation ON finance_credit_note_line
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_customer_payment ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_payment_isolation ON finance_customer_payment;
CREATE POLICY finance_payment_isolation ON finance_customer_payment
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_allocation ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_allocation_isolation ON finance_allocation;
CREATE POLICY finance_allocation_isolation ON finance_allocation
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_customer_refund ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_refund_isolation ON finance_customer_refund;
CREATE POLICY finance_refund_isolation ON finance_customer_refund
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_bill ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_bill_isolation ON finance_bill;
CREATE POLICY finance_bill_isolation ON finance_bill
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_bill_line ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_bill_line_isolation ON finance_bill_line;
CREATE POLICY finance_bill_line_isolation ON finance_bill_line
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_vendor_credit ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_vendor_credit_isolation ON finance_vendor_credit;
CREATE POLICY finance_vendor_credit_isolation ON finance_vendor_credit
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_vendor_credit_line ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_vendor_credit_line_isolation ON finance_vendor_credit_line;
CREATE POLICY finance_vendor_credit_line_isolation ON finance_vendor_credit_line
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_vendor_payment ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_vendor_payment_isolation ON finance_vendor_payment;
CREATE POLICY finance_vendor_payment_isolation ON finance_vendor_payment
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_bill_allocation ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_bill_allocation_isolation ON finance_bill_allocation;
CREATE POLICY finance_bill_allocation_isolation ON finance_bill_allocation
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_vendor_refund ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_vendor_refund_isolation ON finance_vendor_refund;
CREATE POLICY finance_vendor_refund_isolation ON finance_vendor_refund
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_paid_expense ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_paid_expense_isolation ON finance_paid_expense;
CREATE POLICY finance_paid_expense_isolation ON finance_paid_expense
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_paid_expense_line ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_paid_expense_line_isolation ON finance_paid_expense_line;
CREATE POLICY finance_paid_expense_line_isolation ON finance_paid_expense_line
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_purchase_order ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_po_isolation ON finance_purchase_order;
CREATE POLICY finance_po_isolation ON finance_purchase_order
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_purchase_order_line ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_po_line_isolation ON finance_purchase_order_line;
CREATE POLICY finance_po_line_isolation ON finance_purchase_order_line
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_payment_run ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_payment_run_isolation ON finance_payment_run;
CREATE POLICY finance_payment_run_isolation ON finance_payment_run
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_payment_run_line ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_payment_run_line_isolation ON finance_payment_run_line;
CREATE POLICY finance_payment_run_line_isolation ON finance_payment_run_line
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_attachment ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_attachment_isolation ON finance_attachment;
CREATE POLICY finance_attachment_isolation ON finance_attachment
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_bank_statement ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_bank_statement_isolation ON finance_bank_statement;
CREATE POLICY finance_bank_statement_isolation ON finance_bank_statement
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_bank_line ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_bank_line_isolation ON finance_bank_line;
CREATE POLICY finance_bank_line_isolation ON finance_bank_line
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_bank_reconciliation ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_bank_reconciliation_isolation ON finance_bank_reconciliation;
CREATE POLICY finance_bank_reconciliation_isolation ON finance_bank_reconciliation
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_recurring_schedule ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_recurring_schedule_isolation ON finance_recurring_schedule;
CREATE POLICY finance_recurring_schedule_isolation ON finance_recurring_schedule
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_recurring_occurrence ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_recurring_occurrence_isolation ON finance_recurring_occurrence;
CREATE POLICY finance_recurring_occurrence_isolation ON finance_recurring_occurrence
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_reminder_rule ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_reminder_rule_isolation ON finance_reminder_rule;
CREATE POLICY finance_reminder_rule_isolation ON finance_reminder_rule
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_reminder ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_reminder_isolation ON finance_reminder;
CREATE POLICY finance_reminder_isolation ON finance_reminder
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_bank_rule ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_bank_rule_isolation ON finance_bank_rule;
CREATE POLICY finance_bank_rule_isolation ON finance_bank_rule
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_bank_feed ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_bank_feed_isolation ON finance_bank_feed;
CREATE POLICY finance_bank_feed_isolation ON finance_bank_feed
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_saved_filter ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_saved_filter_isolation ON finance_saved_filter;
CREATE POLICY finance_saved_filter_isolation ON finance_saved_filter
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_exception ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_exception_isolation ON finance_exception;
CREATE POLICY finance_exception_isolation ON finance_exception
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_approval_action ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_approval_action_isolation ON finance_approval_action;
CREATE POLICY finance_approval_action_isolation ON finance_approval_action
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_warehouse ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_warehouse_isolation ON finance_warehouse;
CREATE POLICY finance_warehouse_isolation ON finance_warehouse
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_stock_balance ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_stock_balance_isolation ON finance_stock_balance;
CREATE POLICY finance_stock_balance_isolation ON finance_stock_balance
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_stock_move ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_stock_move_isolation ON finance_stock_move;
CREATE POLICY finance_stock_move_isolation ON finance_stock_move
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_fixed_asset ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_fixed_asset_isolation ON finance_fixed_asset;
CREATE POLICY finance_fixed_asset_isolation ON finance_fixed_asset
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_asset_charge ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_asset_charge_isolation ON finance_asset_charge;
CREATE POLICY finance_asset_charge_isolation ON finance_asset_charge
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_reporting_tag ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_reporting_tag_isolation ON finance_reporting_tag;
CREATE POLICY finance_reporting_tag_isolation ON finance_reporting_tag
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_country_pack ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_country_pack_isolation ON finance_country_pack;
CREATE POLICY finance_country_pack_isolation ON finance_country_pack
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_adjustment ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_adjustment_isolation ON finance_adjustment;
CREATE POLICY finance_adjustment_isolation ON finance_adjustment
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_fx_reval ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_fx_reval_isolation ON finance_fx_reval;
CREATE POLICY finance_fx_reval_isolation ON finance_fx_reval
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_webhook_endpoint ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_webhook_endpoint_isolation ON finance_webhook_endpoint;
CREATE POLICY finance_webhook_endpoint_isolation ON finance_webhook_endpoint
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));

ALTER TABLE finance_webhook_delivery ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS finance_webhook_delivery_isolation ON finance_webhook_delivery;
CREATE POLICY finance_webhook_delivery_isolation ON finance_webhook_delivery
  USING (organization_id = current_setting('app.organization_id', true))
  WITH CHECK (organization_id = current_setting('app.organization_id', true));
