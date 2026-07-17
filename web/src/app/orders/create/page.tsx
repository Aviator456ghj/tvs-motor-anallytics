"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import OrderWizardHeader from "@/components/orders/create/OrderWizardHeader";
import OrderSummarySidebar from "@/components/orders/create/OrderSummarySidebar";
import StepCustomer, { type CustomerStepState } from "@/components/orders/create/StepCustomer";
import StepProducts, { type LineItem } from "@/components/orders/create/StepProducts";
import StepShipping from "@/components/orders/create/StepShipping";
import StepPayment from "@/components/orders/create/StepPayment";
import StepReview from "@/components/orders/create/StepReview";
import {
  customers,
  orderableProducts,
  shippingMethods,
  coupons,
  salesChannels,
  warehouses,
  currencies,
  type Coupon,
} from "@/lib/create-order-data";

const TAX_RATE = 0.08;

export default function CreateOrderPage() {
  const router = useRouter();

  const [currentStep, setCurrentStep] = useState(1);
  const [maxReachedStep, setMaxReachedStep] = useState(1);

  const [customerState, setCustomerState] = useState<CustomerStepState>({
    mode: "existing",
    customerId: null,
    billingAddress: null,
    shippingAddress: null,
    salesChannel: salesChannels[0],
    warehouse: warehouses[0],
    currency: currencies[0],
    priority: "Medium",
    tags: [],
    internalNotes: "",
  });

  const [lineItems, setLineItems] = useState<LineItem[]>([]);
  const [shippingMethodId, setShippingMethodId] = useState(shippingMethods[0].id);
  const [deliveryInstructions, setDeliveryInstructions] = useState("");
  const [paymentMethodId, setPaymentMethodId] = useState("");
  const [appliedCoupon, setAppliedCoupon] = useState<Coupon | null>(null);
  const [couponError, setCouponError] = useState<string | null>(null);

  const itemsTotal = useMemo(
    () =>
      lineItems.reduce((sum, li) => {
        const p = orderableProducts.find((x) => x.id === li.productId);
        return sum + (p ? p.price * li.qty : 0);
      }, 0),
    [lineItems]
  );

  const discount = useMemo(() => {
    if (!appliedCoupon) return 0;
    return appliedCoupon.type === "percent" ? (itemsTotal * appliedCoupon.value) / 100 : Math.min(appliedCoupon.value, itemsTotal);
  }, [appliedCoupon, itemsTotal]);

  const shippingCost = shippingMethods.find((m) => m.id === shippingMethodId)?.price ?? 0;
  const tax = Math.max(0, itemsTotal - discount) * TAX_RATE;
  const grandTotal = Math.max(0, itemsTotal - discount) + shippingCost + tax;

  const selectedCustomer = customers.find((c) => c.id === customerState.customerId);
  const fraudRisk = useMemo(() => {
    const reasons: string[] = [];
    if (customerState.mode === "new" || (selectedCustomer && !selectedCustomer.registered)) reasons.push("New/unregistered customer");
    if (grandTotal > 500) reasons.push("High order value");
    if (selectedCustomer && selectedCustomer.outstandingBalance > 0) reasons.push("Outstanding balance on file");
    const level: "Low" | "Medium" | "High" = reasons.length >= 2 ? "High" : reasons.length === 1 ? "Medium" : "Low";
    return { level, reasons };
  }, [customerState.mode, selectedCustomer, grandTotal]);

  function patchCustomer(patch: Partial<CustomerStepState>) {
    setCustomerState((prev) => ({ ...prev, ...patch }));
  }

  function addLineItem(productId: string) {
    setLineItems((prev) => (prev.some((li) => li.productId === productId) ? prev : [...prev, { productId, qty: 1 }]));
  }
  function updateQty(productId: string, qty: number) {
    setLineItems((prev) => prev.map((li) => (li.productId === productId ? { ...li, qty } : li)));
  }
  function removeLineItem(productId: string) {
    setLineItems((prev) => prev.filter((li) => li.productId !== productId));
  }

  function applyCoupon(code: string) {
    const found = coupons.find((c) => c.code === code.trim().toUpperCase());
    if (!found) {
      setCouponError("Coupon code not found.");
      return;
    }
    if (found.used >= found.usageLimit) {
      setCouponError("This coupon has reached its usage limit.");
      return;
    }
    setAppliedCoupon(found);
    setCouponError(null);
  }

  function goToStep(step: number) {
    setCurrentStep(step);
    setMaxReachedStep((m) => Math.max(m, step));
  }

  function handleNextStep() {
    if (currentStep === 1 && customerState.mode === "existing" && !customerState.customerId) return;
    if (currentStep === 2 && lineItems.length === 0) return;
    if (currentStep === 4 && !paymentMethodId) return;
    if (currentStep === 5) {
      console.log("Create order", { customerState, lineItems, shippingMethodId, paymentMethodId, grandTotal });
      router.push("/orders");
      return;
    }
    goToStep(Math.min(5, currentStep + 1));
  }

  function handleQuickAction(id: number) {
    if (id === 1) goToStep(2);
    else if (id === 4) goToStep(1);
    else console.log("quick action", id);
  }

  return (
    <div className="flex flex-col gap-5 max-w-[1600px] mx-auto">
      <OrderWizardHeader
        currentStep={currentStep}
        maxReachedStep={maxReachedStep}
        onStepClick={goToStep}
        onCancel={() => router.push("/orders")}
        onSaveDraft={() => console.log("save draft", { customerState, lineItems })}
        onNextStep={handleNextStep}
        isLastStep={currentStep === 5}
      />

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_280px] gap-5 items-start">
        <div className="min-w-0">
          {currentStep === 1 && <StepCustomer state={customerState} onChange={patchCustomer} />}
          {currentStep === 2 && (
            <StepProducts lineItems={lineItems} onAdd={addLineItem} onUpdateQty={updateQty} onRemove={removeLineItem} />
          )}
          {currentStep === 3 && (
            <StepShipping
              selectedId={shippingMethodId}
              onSelect={setShippingMethodId}
              instructions={deliveryInstructions}
              onInstructionsChange={setDeliveryInstructions}
            />
          )}
          {currentStep === 4 && <StepPayment selectedId={paymentMethodId} onSelect={setPaymentMethodId} grandTotal={grandTotal} />}
          {currentStep === 5 && (
            <StepReview
              customerState={customerState}
              lineItems={lineItems}
              shippingMethodId={shippingMethodId}
              paymentMethodId={paymentMethodId}
              fraudRisk={fraudRisk}
              onEditStep={goToStep}
            />
          )}
        </div>

        <OrderSummarySidebar
          itemsTotal={itemsTotal}
          discount={discount}
          shipping={shippingCost}
          taxRate={TAX_RATE}
          tax={tax}
          grandTotal={grandTotal}
          savings={discount}
          appliedCoupon={appliedCoupon}
          onApplyCoupon={applyCoupon}
          onRemoveCoupon={() => setAppliedCoupon(null)}
          couponError={couponError}
          onQuickAction={handleQuickAction}
        />
      </div>
    </div>
  );
}
