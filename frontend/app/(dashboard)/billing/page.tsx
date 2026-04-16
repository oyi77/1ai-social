'use client';

import { useEffect, useState } from 'react';
import { Check, CreditCard, Download } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { api } from '@/lib/api';
import type { Subscription, Invoice, BillingPlan } from '@/types';
import { formatCurrency, formatDate } from '@/lib/utils';

const plans: BillingPlan[] = [
  {
    id: 'starter',
    name: 'Starter',
    price: 29,
    interval: 'month',
    features: [
      '50 posts per month',
      '1,000 API calls per day',
      '3 social platforms',
      'Basic analytics',
      'Email support',
    ],
    limits: {
      postsPerMonth: 50,
      apiCallsPerDay: 1000,
      platforms: 3,
    },
  },
  {
    id: 'pro',
    name: 'Pro',
    price: 99,
    interval: 'month',
    features: [
      '200 posts per month',
      '10,000 API calls per day',
      '5 social platforms',
      'Advanced analytics',
      'Priority support',
      'Custom scheduling',
    ],
    limits: {
      postsPerMonth: 200,
      apiCallsPerDay: 10000,
      platforms: 5,
    },
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: 299,
    interval: 'month',
    features: [
      'Unlimited posts',
      'Unlimited API calls',
      'All social platforms',
      'Custom analytics',
      '24/7 support',
      'Dedicated account manager',
      'Custom integrations',
    ],
    limits: {
      postsPerMonth: -1,
      apiCallsPerDay: -1,
      platforms: -1,
    },
  },
];

export default function BillingPage() {
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUpgrading, setIsUpgrading] = useState(false);

  useEffect(() => {
    fetchBillingData();
  }, []);

  const fetchBillingData = async () => {
    try {
      const [subData, invoicesData] = await Promise.all([
        api.getSubscription(),
        api.getInvoices(),
      ]);
      setSubscription(subData);
      setInvoices(invoicesData);
    } catch (error) {
      console.error('Failed to fetch billing data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpgrade = async (planId: string) => {
    if (!confirm('Are you sure you want to change your plan?')) return;

    setIsUpgrading(true);
    try {
      await api.updateSubscription(planId);
      fetchBillingData();
    } catch (error) {
      console.error('Failed to update subscription:', error);
      alert('Failed to update subscription');
    } finally {
      setIsUpgrading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const currentPlanId = subscription?.plan.id;
  const usage = subscription?.usage;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Billing</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">
          Manage your subscription and billing
        </p>
      </div>

      {subscription && (
        <Card>
          <CardHeader>
            <CardTitle>Current Plan</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  {subscription.plan.name}
                </h3>
                <p className="text-gray-600 dark:text-gray-400 mt-1">
                  {formatCurrency(subscription.plan.price)}/{subscription.plan.interval}
                </p>
              </div>
              <div className={`px-4 py-2 rounded-full text-sm font-medium ${
                subscription.status === 'active'
                  ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                  : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
              }`}>
                {subscription.status}
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Posts Used</span>
                  <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {usage?.postsUsed || 0} / {subscription.plan.limits.postsPerMonth === -1 ? '∞' : subscription.plan.limits.postsPerMonth}
                  </span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full"
                    style={{
                      width: subscription.plan.limits.postsPerMonth === -1
                        ? '0%'
                        : `${Math.min(((usage?.postsUsed || 0) / subscription.plan.limits.postsPerMonth) * 100, 100)}%`,
                    }}
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600 dark:text-gray-400">API Calls Used (Today)</span>
                  <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {usage?.apiCallsUsed || 0} / {subscription.plan.limits.apiCallsPerDay === -1 ? '∞' : subscription.plan.limits.apiCallsPerDay}
                  </span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full"
                    style={{
                      width: subscription.plan.limits.apiCallsPerDay === -1
                        ? '0%'
                        : `${Math.min(((usage?.apiCallsUsed || 0) / subscription.plan.limits.apiCallsPerDay) * 100, 100)}%`,
                    }}
                  />
                </div>
              </div>
            </div>

            <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Next billing date: {formatDate(subscription.currentPeriodEnd)}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">Available Plans</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {plans.map((plan) => {
            const isCurrent = plan.id === currentPlanId;
            
            return (
              <Card key={plan.id} className={isCurrent ? 'border-2 border-blue-500' : ''}>
                <CardContent className="p-6">
                  <div className="text-center mb-6">
                    <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100">
                      {plan.name}
                    </h3>
                    <div className="mt-4">
                      <span className="text-4xl font-bold text-gray-900 dark:text-gray-100">
                        {formatCurrency(plan.price)}
                      </span>
                      <span className="text-gray-600 dark:text-gray-400">/{plan.interval}</span>
                    </div>
                  </div>

                  <ul className="space-y-3 mb-6">
                    {plan.features.map((feature, index) => (
                      <li key={index} className="flex items-start gap-3">
                        <Check className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
                        <span className="text-sm text-gray-700 dark:text-gray-300">{feature}</span>
                      </li>
                    ))}
                  </ul>

                  <Button
                    onClick={() => handleUpgrade(plan.id)}
                    variant={isCurrent ? 'secondary' : 'primary'}
                    className="w-full"
                    disabled={isCurrent || isUpgrading}
                  >
                    {isCurrent ? 'Current Plan' : 'Upgrade'}
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Invoice History</CardTitle>
        </CardHeader>
        <CardContent>
          {invoices.length === 0 ? (
            <p className="text-center py-8 text-gray-600 dark:text-gray-400">
              No invoices yet
            </p>
          ) : (
            <div className="space-y-3">
              {invoices.map((invoice) => (
                <div
                  key={invoice.id}
                  className="flex items-center justify-between p-4 border border-gray-200 dark:border-gray-700 rounded-lg"
                >
                  <div className="flex items-center gap-4">
                    <CreditCard className="w-5 h-5 text-gray-400" />
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {formatCurrency(invoice.amount)}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {formatDate(invoice.date)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      invoice.status === 'paid'
                        ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                        : invoice.status === 'pending'
                        ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                        : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                    }`}>
                      {invoice.status}
                    </span>
                    {invoice.downloadUrl && (
                      <Button variant="ghost" size="sm">
                        <Download className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
