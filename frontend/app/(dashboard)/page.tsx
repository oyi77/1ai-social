'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { BarChart3, FileText, Users, TrendingUp } from 'lucide-react';
import { StatCard } from '@/components/dashboard/StatCard';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { api } from '@/lib/api';
import { isAuthenticated } from '@/lib/auth';
import type { DashboardStats, Post } from '@/types';
import { formatDate, formatNumber } from '@/lib/utils';

export default function DashboardPage() {
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentPosts, setRecentPosts] = useState<Post[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login');
      return;
    }

    const fetchData = async () => {
      try {
        const [statsData, postsData] = await Promise.all([
          api.getDashboardStats(),
          api.getPosts({ limit: 5 }),
        ]);
        setStats(statsData);
        setRecentPosts(postsData);
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [router]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Dashboard</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">Welcome back! Here's your overview.</p>
        </div>
        <Button onClick={() => router.push('/dashboard/posts/new')}>
          Create Post
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Posts This Month"
          value={formatNumber(stats?.postsThisMonth || 0)}
          icon={FileText}
          trend={{ value: 12, isPositive: true }}
        />
        <StatCard
          title="Total Views"
          value={formatNumber(stats?.totalViews || 0)}
          icon={BarChart3}
          trend={{ value: 8, isPositive: true }}
        />
        <StatCard
          title="Engagement Rate"
          value={`${((stats?.totalEngagement || 0) / (stats?.totalViews || 1) * 100).toFixed(1)}%`}
          icon={TrendingUp}
          trend={{ value: 5, isPositive: true }}
        />
        <StatCard
          title="Connected Accounts"
          value={stats?.connectedAccounts || 0}
          icon={Users}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Recent Posts</CardTitle>
          </CardHeader>
          <CardContent>
            {recentPosts.length === 0 ? (
              <div className="text-center py-8">
                <FileText className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                <p className="text-gray-600 dark:text-gray-400">No posts yet</p>
                <Button
                  variant="outline"
                  className="mt-4"
                  onClick={() => router.push('/dashboard/posts/new')}
                >
                  Create your first post
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                {recentPosts.map((post) => (
                  <div
                    key={post.id}
                    className="flex items-start justify-between p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors cursor-pointer"
                    onClick={() => router.push(`/dashboard/posts/${post.id}`)}
                  >
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100 line-clamp-2">
                        {post.content}
                      </p>
                      <div className="flex items-center gap-3 mt-2">
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {formatDate(post.createdAt)}
                        </span>
                        <span className={`text-xs px-2 py-1 rounded-full ${
                          post.status === 'published'
                            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                            : post.status === 'scheduled'
                            ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                            : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-400'
                        }`}>
                          {post.status}
                        </span>
                      </div>
                    </div>
                    {post.analytics && (
                      <div className="ml-4 text-right">
                        <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                          {formatNumber(post.analytics.views)}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">views</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <Button
                variant="outline"
                className="w-full justify-start"
                onClick={() => router.push('/dashboard/posts/new')}
              >
                <FileText className="w-4 h-4 mr-2" />
                Create New Post
              </Button>
              <Button
                variant="outline"
                className="w-full justify-start"
                onClick={() => router.push('/dashboard/accounts')}
              >
                <Users className="w-4 h-4 mr-2" />
                Connect Social Account
              </Button>
              <Button
                variant="outline"
                className="w-full justify-start"
                onClick={() => router.push('/dashboard/analytics')}
              >
                <BarChart3 className="w-4 h-4 mr-2" />
                View Analytics
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
