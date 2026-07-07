import React, { forwardRef } from 'react';
import './Input.css';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  fullWidth?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, leftIcon, rightIcon, fullWidth = true, className = '', ...props }, ref) => {
    return (
      <div className={`input-wrapper ${fullWidth ? 'full-width' : ''} ${className}`}>
        {label && <label className="input-label">{label}</label>}
        
        <div className={`input-container ${error ? 'has-error' : ''}`}>
          {leftIcon && <div className="input-icon-left">{leftIcon}</div>}
          
          <input
            ref={ref}
            className={`input-field ${leftIcon ? 'with-left-icon' : ''} ${rightIcon ? 'with-right-icon' : ''}`}
            {...props}
          />
          
          {rightIcon && <div className="input-icon-right">{rightIcon}</div>}
        </div>
        
        {error && <p className="input-error-text animate-slide-up">{error}</p>}
      </div>
    );
  }
);

Input.displayName = 'Input';
