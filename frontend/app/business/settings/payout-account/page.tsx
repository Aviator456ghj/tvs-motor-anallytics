"use client";

import { useEffect, useState } from "react";
import { PageHeader, Spinner } from "@/components/ui";
import { useToast } from "@/components/Toast";
import { api, ApiError } from "@/lib/api";

interface PayoutAccount {
  account_holder_name: string;
  bank_name: string;
  account_number_last4: string;
  ifsc_code: string;
  upi_id: string | null;
  is_verified: boolean;
}

export default function PayoutAccountPage() {
  const toast = useToast();
  const [account, setAccount] = useState<PayoutAccount | null | undefined>(undefined);
  const [form, setForm] = useState({ account_holder_name: "", bank_name: "", account_number: "", ifsc_code: "", upi_id: "" });
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get<PayoutAccount | null>("/businesses/me/payout-account").then((a) => {
      setAccount(a);
      if (a) setForm({ account_holder_name: a.account_holder_name, bank_name: a.bank_name, account_number: "", ifsc_code: a.ifsc_code, upi_id: a.upi_id || "" });
    });
  }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const updated = await api.put<PayoutAccount>("/businesses/me/payout-account", form);
      setAccount(updated);
      toast("Payout account saved", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Could not save payout account", "error");
    } finally {
      setBusy(false);
    }
  }

  if (account === undefined) return <Spinner />;

  return (
    <div className="max-w-lg">
      <PageHeader title="Payout account" description="Where your earnings are sent when you request a payout." />
      {account && (
        <div className="card mb-6 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-slate-800">{account.bank_name} •••• {account.account_number_last4}</p>
            <p className="text-xs text-slate-500">{account.account_holder_name}</p>
          </div>
          <span className={`badge ${account.is_verified ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}>
            {account.is_verified ? "Verified" : "Pending verification"}
          </span>
        </div>
      )}
      <form onSubmit={save} className="card space-y-4">
        <div>
          <label className="label">Account holder name</label>
          <input className="input" required value={form.account_holder_name} onChange={(e) => setForm({ ...form, account_holder_name: e.target.value })} />
        </div>
        <div>
          <label className="label">Bank name</label>
          <input className="input" required value={form.bank_name} onChange={(e) => setForm({ ...form, bank_name: e.target.value })} />
        </div>
        <div>
          <label className="label">Account number</label>
          <input className="input" required placeholder={account ? "Enter to replace saved account" : ""} value={form.account_number} onChange={(e) => setForm({ ...form, account_number: e.target.value })} />
          <p className="mt-1 text-xs text-slate-400">Only the last 4 digits are stored — the rest never touches our database.</p>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">IFSC code</label>
            <input className="input" required value={form.ifsc_code} onChange={(e) => setForm({ ...form, ifsc_code: e.target.value })} />
          </div>
          <div>
            <label className="label">UPI ID (optional)</label>
            <input className="input" value={form.upi_id} onChange={(e) => setForm({ ...form, upi_id: e.target.value })} />
          </div>
        </div>
        <button className="btn-primary" disabled={busy}>{busy ? "Saving…" : account ? "Update account" : "Save account"}</button>
      </form>
    </div>
  );
}
