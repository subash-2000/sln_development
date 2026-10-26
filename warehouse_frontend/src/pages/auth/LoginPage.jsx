import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useAuth } from '../../hooks/use-auth';
import Card from '../../components/ui/Card';
import Input from '../../components/ui/Input';
import Button from '../../components/ui/Button';
import { AlertCircle } from 'lucide-react';

const loginSchema = z.object({
  username: z.string().min(3, 'Username must be at least 3 characters'),
  password: z.string().min(1, 'Password is required'),
  rememberMe: z.boolean().optional(),
});

const LoginPage = () => {
  const { login, isLoggingIn, loginError } = useAuth();
  
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      username: '',
      password: '',
      rememberMe: false,
    },
  });

  const onSubmit = async (data) => {
    try {
      await login({
        username_or_email: data.username,
        password: data.password,
      });
    } catch (err) {
      // Error is handled by useAuth mutation state
      console.error('Login failed', err);
    }
  };

  return (
    <Card className="shadow-clay-lg">
      <Card.Header>
        <Card.Title>Sign In</Card.Title>
        <p className="text-sm text-gray-500 mt-1">Access your warehouse dashboard</p>
      </Card.Header>
      <Card.Body>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {loginError && (
            <div className="bg-red-50 border border-red-100 text-red-700 px-4 py-3 rounded-lg flex items-start space-x-3 text-sm">
              <AlertCircle size={18} className="flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Login Failed</p>
                <p>{loginError.message}</p>
                {loginError.requestId && (
                  <p className="mt-1 text-xs opacity-70">Request ID: {loginError.requestId}</p>
                )}
              </div>
            </div>
          )}

          <Input
            label="Username"
            placeholder="Enter your username"
            error={errors.username?.message}
            isRequired
            {...register('username')}
          />

          <Input
            label="Password"
            type="password"
            placeholder="••••••••"
            error={errors.password?.message}
            isRequired
            {...register('password')}
          />

          <div className="flex items-center justify-between">
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                {...register('rememberMe')}
              />
              <span className="text-sm text-gray-600">Keep me signed in on this device</span>
            </label>
          </div>

          <Button 
            type="submit" 
            className="w-full" 
            isLoading={isLoggingIn}
          >
            Sign In
          </Button>
        </form>
      </Card.Body>
      <Card.Footer className="text-center">
        <p className="text-xs text-gray-400">
          © 2026 SLN Warehouse Management System. All rights reserved.
        </p>
      </Card.Footer>
    </Card>
  );
};

export default LoginPage;
