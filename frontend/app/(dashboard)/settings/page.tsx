'use client';

import { useEffect, useState } from 'react';
import { User, Key, Users as UsersIcon, Copy, Trash2, Plus } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Modal } from '@/components/ui/Modal';
import { api } from '@/lib/api';
import type { User as UserType, ApiKey, TeamMember } from '@/types';
import { formatDate } from '@/lib/utils';

export default function SettingsPage() {
  const [user, setUser] = useState<UserType | null>(null);
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  
  const [showApiKeyModal, setShowApiKeyModal] = useState(false);
  const [newApiKeyName, setNewApiKeyName] = useState('');
  
  const [showTeamModal, setShowTeamModal] = useState(false);
  const [newMemberEmail, setNewMemberEmail] = useState('');
  const [newMemberRole, setNewMemberRole] = useState('member');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [userData, keysData, teamData] = await Promise.all([
        api.getMe(),
        api.getApiKeys(),
        api.getTeamMembers(),
      ]);
      setUser(userData);
      setName(userData.name);
      setEmail(userData.email);
      setApiKeys(keysData);
      setTeamMembers(teamData);
    } catch (error) {
      console.error('Failed to fetch settings:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdateProfile = async () => {
    try {
      await api.updateProfile({ name, email });
      alert('Profile updated successfully');
      fetchData();
    } catch (error) {
      console.error('Failed to update profile:', error);
      alert('Failed to update profile');
    }
  };

  const handleCreateApiKey = async () => {
    if (!newApiKeyName.trim()) {
      alert('Please enter a key name');
      return;
    }

    try {
      await api.createApiKey(newApiKeyName);
      setShowApiKeyModal(false);
      setNewApiKeyName('');
      fetchData();
    } catch (error) {
      console.error('Failed to create API key:', error);
      alert('Failed to create API key');
    }
  };

  const handleRevokeApiKey = async (keyId: string) => {
    if (!confirm('Are you sure you want to revoke this API key?')) return;

    try {
      await api.revokeApiKey(keyId);
      fetchData();
    } catch (error) {
      console.error('Failed to revoke API key:', error);
      alert('Failed to revoke API key');
    }
  };

  const handleCopyApiKey = (key: string) => {
    navigator.clipboard.writeText(key);
    alert('API key copied to clipboard');
  };

  const handleInviteTeamMember = async () => {
    if (!newMemberEmail.trim()) {
      alert('Please enter an email address');
      return;
    }

    try {
      await api.inviteTeamMember(newMemberEmail, newMemberRole);
      setShowTeamModal(false);
      setNewMemberEmail('');
      setNewMemberRole('member');
      fetchData();
    } catch (error) {
      console.error('Failed to invite team member:', error);
      alert('Failed to invite team member');
    }
  };

  const handleRemoveTeamMember = async (memberId: string) => {
    if (!confirm('Are you sure you want to remove this team member?')) return;

    try {
      await api.removeTeamMember(memberId);
      fetchData();
    } catch (error) {
      console.error('Failed to remove team member:', error);
      alert('Failed to remove team member');
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Settings</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">
          Manage your account settings and preferences
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Profile Settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input
            label="Full Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="John Doe"
          />
          <Input
            label="Email Address"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
          />
          <Button onClick={handleUpdateProfile}>
            Save Changes
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>API Keys</CardTitle>
            <Button size="sm" onClick={() => setShowApiKeyModal(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Create Key
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {apiKeys.length === 0 ? (
            <p className="text-center py-8 text-gray-600 dark:text-gray-400">
              No API keys yet
            </p>
          ) : (
            <div className="space-y-3">
              {apiKeys.map((key) => (
                <div
                  key={key.id}
                  className="flex items-center justify-between p-4 border border-gray-200 dark:border-gray-700 rounded-lg"
                >
                  <div className="flex items-center gap-4">
                    <Key className="w-5 h-5 text-gray-400" />
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {key.name}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 font-mono">
                        {key.key.substring(0, 20)}...
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        Created {formatDate(key.createdAt)}
                        {key.lastUsed && ` • Last used ${formatDate(key.lastUsed)}`}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleCopyApiKey(key.key)}
                    >
                      <Copy className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRevokeApiKey(key.id)}
                    >
                      <Trash2 className="w-4 h-4 text-red-600" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Team Members</CardTitle>
            <Button size="sm" onClick={() => setShowTeamModal(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Invite Member
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {teamMembers.length === 0 ? (
            <p className="text-center py-8 text-gray-600 dark:text-gray-400">
              No team members yet
            </p>
          ) : (
            <div className="space-y-3">
              {teamMembers.map((member) => (
                <div
                  key={member.id}
                  className="flex items-center justify-between p-4 border border-gray-200 dark:border-gray-700 rounded-lg"
                >
                  <div className="flex items-center gap-4">
                    <UsersIcon className="w-5 h-5 text-gray-400" />
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {member.name}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {member.email}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        Invited {formatDate(member.invitedAt)} • {member.role}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      member.status === 'active'
                        ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                        : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                    }`}>
                      {member.status}
                    </span>
                    {member.role !== 'owner' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRemoveTeamMember(member.id)}
                      >
                        <Trash2 className="w-4 h-4 text-red-600" />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Modal
        isOpen={showApiKeyModal}
        onClose={() => setShowApiKeyModal(false)}
        title="Create API Key"
      >
        <div className="space-y-4">
          <Input
            label="Key Name"
            value={newApiKeyName}
            onChange={(e) => setNewApiKeyName(e.target.value)}
            placeholder="Production API Key"
          />
          <div className="flex gap-3">
            <Button onClick={handleCreateApiKey} className="flex-1">
              Create Key
            </Button>
            <Button variant="outline" onClick={() => setShowApiKeyModal(false)} className="flex-1">
              Cancel
            </Button>
          </div>
        </div>
      </Modal>

      <Modal
        isOpen={showTeamModal}
        onClose={() => setShowTeamModal(false)}
        title="Invite Team Member"
      >
        <div className="space-y-4">
          <Input
            label="Email Address"
            type="email"
            value={newMemberEmail}
            onChange={(e) => setNewMemberEmail(e.target.value)}
            placeholder="colleague@example.com"
          />
          <Select
            label="Role"
            value={newMemberRole}
            onChange={(e) => setNewMemberRole(e.target.value)}
            options={[
              { value: 'member', label: 'Member' },
              { value: 'admin', label: 'Admin' },
            ]}
          />
          <div className="flex gap-3">
            <Button onClick={handleInviteTeamMember} className="flex-1">
              Send Invite
            </Button>
            <Button variant="outline" onClick={() => setShowTeamModal(false)} className="flex-1">
              Cancel
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
