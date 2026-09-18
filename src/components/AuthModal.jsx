import React, { useState } from 'react';
import { X, Eye, EyeOff, Lock, Mail, User, ShieldCheck } from 'lucide-react';

export default function AuthModal({ isOpen, onClose, initialMode = 'signin', onSuccess }) {
  const [mode, setMode] = useState(initialMode); // 'signin' or 'signup'
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    institution: ''
  });
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const validate = () => {
    const errs = {};
    if (!formData.email || !formData.email.includes('@')) {
      errs.email = 'Valid institutional email address is required.';
    }
    if (!formData.password || formData.password.length < 6) {
      errs.password = 'Password must be at least 6 characters long.';
    }
    if (mode === 'signup' && !formData.name) {
      errs.name = 'Researcher name is required.';
    }
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!validate()) return;

    setIsSubmitting(true);
    setTimeout(() => {
      setIsSubmitting(false);
      onSuccess({
        name: formData.name || formData.email.split('@')[0],
        email: formData.email,
        institution: formData.institution || 'Medical Research Institute'
      });
      onClose();
    }, 600);
  };

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in"
      role="dialog"
      aria-modal="true"
      aria-labelledby="auth-modal-title"
    >
      <div className="relative w-full max-w-md bg-[var(--color-card-white)] rounded-[24px] p-6 sm:p-8 shadow-2xl border border-[var(--color-border-subtle)] text-[var(--color-cocoa-text)]">
        
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-full hover:bg-[var(--color-cream-surface)] text-[var(--color-cocoa-subtext)] transition-colors"
          aria-label="Close authentication modal"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="text-center mb-6">
          <div className="w-12 h-12 rounded-2xl bg-[#6B1D2F] text-white flex items-center justify-center mx-auto mb-3 shadow-md">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <h2 id="auth-modal-title" className="font-serif text-2xl font-bold">
            {mode === 'signin' ? 'Researcher Sign In' : 'Create Synora Account'}
          </h2>
          <p className="text-xs text-[var(--color-cocoa-subtext)] mt-1">
            Access evidence-based synthetic cohort generation and symmetric privacy gates.
          </p>
        </div>

        {/* Form Inputs with Fast Forms Real-time Validation */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === 'signup' && (
            <div>
              <label className="block text-xs font-semibold mb-1">Full Name</label>
              <div className="relative">
                <User className="absolute left-3.5 top-3 w-4 h-4 text-[var(--color-cocoa-subtext)]" />
                <input
                  type="text"
                  placeholder="Dr. Evelyn Vance"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full pl-10 pr-4 py-2.5 text-xs rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-cream-surface)] focus:ring-2 focus:ring-[#6B1D2F] focus:outline-none"
                />
              </div>
              {errors.name && <p className="text-[10px] text-red-500 mt-1">{errors.name}</p>}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold mb-1">Institutional Email</label>
            <div className="relative">
              <Mail className="absolute left-3.5 top-3 w-4 h-4 text-[var(--color-cocoa-subtext)]" />
              <input
                type="email"
                placeholder="researcher@stanford.edu"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full pl-10 pr-4 py-2.5 text-xs rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-cream-surface)] focus:ring-2 focus:ring-[#6B1D2F] focus:outline-none"
              />
            </div>
            {errors.email && <p className="text-[10px] text-red-500 mt-1">{errors.email}</p>}
          </div>

          {/* Password Input with Visibility Toggle */}
          <div>
            <label className="block text-xs font-semibold mb-1">Password</label>
            <div className="relative">
              <Lock className="absolute left-3.5 top-3 w-4 h-4 text-[var(--color-cocoa-subtext)]" />
              <input
                type={showPassword ? 'text' : 'password'}
                placeholder="••••••••••••"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="w-full pl-10 pr-10 py-2.5 text-xs rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-cream-surface)] focus:ring-2 focus:ring-[#6B1D2F] focus:outline-none"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-2.5 text-[var(--color-cocoa-subtext)] hover:text-[var(--color-cocoa-text)] transition-colors"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                title={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            {errors.password && <p className="text-[10px] text-red-500 mt-1">{errors.password}</p>}
          </div>

          {mode === 'signup' && (
            <div>
              <label className="block text-xs font-semibold mb-1">Institution / Research Lab (Optional)</label>
              <input
                type="text"
                placeholder="Broad Institute of MIT and Harvard"
                value={formData.institution}
                onChange={(e) => setFormData({ ...formData, institution: e.target.value })}
                className="w-full px-4 py-2.5 text-xs rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-cream-surface)] focus:ring-2 focus:ring-[#6B1D2F] focus:outline-none"
              />
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-3 mt-2 bg-[#6B1D2F] hover:bg-[#8B263E] text-white text-xs font-bold rounded-xl shadow-lg transition-all hover:scale-[1.02] flex items-center justify-center gap-2"
          >
            {isSubmitting ? 'Authenticating...' : mode === 'signin' ? 'Sign In to Workspace' : 'Register Researcher Account'}
          </button>
        </form>

        {/* Footer Toggle */}
        <div className="mt-6 pt-4 border-t border-[var(--color-border-subtle)] text-center text-xs text-[var(--color-cocoa-subtext)]">
          {mode === 'signin' ? (
            <span>
              Don't have a Synora account?{' '}
              <button
                onClick={() => { setMode('signup'); setErrors({}); }}
                className="font-bold text-[#6B1D2F] dark:text-[#E89B72] hover:underline"
              >
                Sign Up
              </button>
            </span>
          ) : (
            <span>
              Already registered?{' '}
              <button
                onClick={() => { setMode('signin'); setErrors({}); }}
                className="font-bold text-[#6B1D2F] dark:text-[#E89B72] hover:underline"
              >
                Sign In
              </button>
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
