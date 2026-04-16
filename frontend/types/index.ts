export interface User {
  id: string;
  email: string;
  name: string;
  avatar?: string;
  createdAt: string;
}

export interface AuthResponse {
  token: string;
  user: User;
}

export interface SocialAccount {
  id: string;
  platform: 'twitter' | 'instagram' | 'tiktok' | 'linkedin' | 'facebook';
  username: string;
  avatar?: string;
  isConnected: boolean;
  connectedAt?: string;
  followers?: number;
}

export interface Post {
  id: string;
  content: string;
  platforms: string[];
  status: 'draft' | 'scheduled' | 'published' | 'failed';
  scheduledAt?: string;
  publishedAt?: string;
  mediaUrls?: string[];
  analytics?: PostAnalytics;
  createdAt: string;
}

export interface PostAnalytics {
  views: number;
  likes: number;
  comments: number;
  shares: number;
  engagement: number;
}

export interface DashboardStats {
  totalPosts: number;
  totalViews: number;
  totalEngagement: number;
  connectedAccounts: number;
  postsThisMonth: number;
  viewsThisMonth: number;
}

export interface AnalyticsData {
  date: string;
  views: number;
  engagement: number;
  posts: number;
}

export interface BillingPlan {
  id: string;
  name: 'Starter' | 'Pro' | 'Enterprise';
  price: number;
  interval: 'month' | 'year';
  features: string[];
  limits: {
    postsPerMonth: number;
    apiCallsPerDay: number;
    platforms: number;
  };
}

export interface Subscription {
  id: string;
  plan: BillingPlan;
  status: 'active' | 'canceled' | 'past_due';
  currentPeriodEnd: string;
  usage: {
    postsUsed: number;
    apiCallsUsed: number;
  };
}

export interface Invoice {
  id: string;
  amount: number;
  status: 'paid' | 'pending' | 'failed';
  date: string;
  downloadUrl?: string;
}

export interface ApiKey {
  id: string;
  name: string;
  key: string;
  createdAt: string;
  lastUsed?: string;
}

export interface TeamMember {
  id: string;
  email: string;
  name: string;
  role: 'owner' | 'admin' | 'member';
  invitedAt: string;
  status: 'active' | 'pending';
}
