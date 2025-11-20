/**
 * Form Submission Hook
 * 
 * Handles form submission with validation, loading states, and error handling
 */

import { useState, useCallback } from "react";
import { validateForm, ValidationResult } from "@/lib/form-validation";

export interface FormSubmissionOptions<T> {
  onSubmit: (values: T) => Promise<void>;
  onSuccess?: (values: T) => void;
  onError?: (error: Error) => void;
  validationRules?: Partial<Record<keyof T, (value: any) => ValidationResult>>;
  resetOnSuccess?: boolean;
}

export interface FormSubmissionState<T> {
  values: T;
  errors: Partial<Record<keyof T, string>>;
  isSubmitting: boolean;
  isValid: boolean;
  submitCount: number;
}

export function useFormSubmission<T extends Record<string, any>>(
  initialValues: T,
  options: FormSubmissionOptions<T>
) {
  const {
    onSubmit,
    onSuccess,
    onError,
    validationRules = {},
    resetOnSuccess = false,
  } = options;

  const [values, setValues] = useState<T>(initialValues);
  const [errors, setErrors] = useState<Partial<Record<keyof T, string>>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitCount, setSubmitCount] = useState(0);

  /**
   * Update a single field value
   */
  const setValue = useCallback((field: keyof T, value: any) => {
    setValues((prev) => ({ ...prev, [field]: value }));
    
    // Clear error for this field when user starts typing
    setErrors((prev) => {
      const newErrors = { ...prev };
      delete newErrors[field];
      return newErrors;
    });
  }, []);

  /**
   * Update multiple field values
   */
  const setFieldValues = useCallback((newValues: Partial<T>) => {
    setValues((prev) => ({ ...prev, ...newValues }));
  }, []);

  /**
   * Set error for a specific field
   */
  const setFieldError = useCallback((field: keyof T, error: string) => {
    setErrors((prev) => ({ ...prev, [field]: error }));
  }, []);

  /**
   * Clear all errors
   */
  const clearErrors = useCallback(() => {
    setErrors({});
  }, []);

  /**
   * Reset form to initial values
   */
  const reset = useCallback(() => {
    setValues(initialValues);
    setErrors({});
    setSubmitCount(0);
  }, [initialValues]);

  /**
   * Validate all fields
   */
  const validate = useCallback((): boolean => {
    const validation = validateForm(values, validationRules);
    setErrors(validation.errors);
    return validation.isValid;
  }, [values, validationRules]);

  /**
   * Handle form submission
   */
  const handleSubmit = useCallback(
    async (e?: React.FormEvent) => {
      if (e) {
        e.preventDefault();
      }

      setSubmitCount((prev) => prev + 1);

      // Validate form
      if (!validate()) {
        return;
      }

      setIsSubmitting(true);

      try {
        await onSubmit(values);
        
        if (onSuccess) {
          onSuccess(values);
        }

        if (resetOnSuccess) {
          reset();
        }
      } catch (error) {
        const err = error instanceof Error ? error : new Error("Submission failed");
        
        if (onError) {
          onError(err);
        }
      } finally {
        setIsSubmitting(false);
      }
    },
    [values, validate, onSubmit, onSuccess, onError, reset, resetOnSuccess]
  );

  /**
   * Check if form is valid
   */
  const isValid = Object.keys(errors).length === 0;

  return {
    values,
    errors,
    isSubmitting,
    isValid,
    submitCount,
    setValue,
    setFieldValues,
    setFieldError,
    clearErrors,
    reset,
    validate,
    handleSubmit,
  };
}
