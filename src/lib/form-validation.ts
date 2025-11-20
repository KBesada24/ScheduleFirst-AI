/**
 * Form Validation Utilities
 * 
 * Comprehensive validation functions for form fields
 */

export interface ValidationResult {
  isValid: boolean;
  error?: string;
}

export interface ValidationRule {
  validate: (value: any) => boolean;
  message: string;
}

// ============================================
// BASIC VALIDATORS
// ============================================

/**
 * Check if value is not empty
 */
export function required(value: any): ValidationResult {
  const isValid = value !== null && value !== undefined && value !== "";
  return {
    isValid,
    error: isValid ? undefined : "This field is required",
  };
}

/**
 * Check if value is a valid email
 */
export function email(value: string): ValidationResult {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const isValid = !value || emailRegex.test(value);
  return {
    isValid,
    error: isValid ? undefined : "Please enter a valid email address",
  };
}

/**
 * Check if value meets minimum length
 */
export function minLength(min: number) {
  return (value: string): ValidationResult => {
    const isValid = !value || value.length >= min;
    return {
      isValid,
      error: isValid ? undefined : `Must be at least ${min} characters`,
    };
  };
}

/**
 * Check if value meets maximum length
 */
export function maxLength(max: number) {
  return (value: string): ValidationResult => {
    const isValid = !value || value.length <= max;
    return {
      isValid,
      error: isValid ? undefined : `Must be at most ${max} characters`,
    };
  };
}

/**
 * Check if value is within a range
 */
export function range(min: number, max: number) {
  return (value: number): ValidationResult => {
    const isValid = value >= min && value <= max;
    return {
      isValid,
      error: isValid ? undefined : `Must be between ${min} and ${max}`,
    };
  };
}

/**
 * Check if value matches a pattern
 */
export function pattern(regex: RegExp, message: string = "Invalid format") {
  return (value: string): ValidationResult => {
    const isValid = !value || regex.test(value);
    return {
      isValid,
      error: isValid ? undefined : message,
    };
  };
}

/**
 * Check if value matches another field
 */
export function matches(otherValue: any, fieldName: string = "field") {
  return (value: any): ValidationResult => {
    const isValid = value === otherValue;
    return {
      isValid,
      error: isValid ? undefined : `Must match ${fieldName}`,
    };
  };
}

// ============================================
// SPECIFIC VALIDATORS
// ============================================

/**
 * Validate password strength
 */
export function password(value: string): ValidationResult {
  if (!value) {
    return { isValid: true };
  }

  const hasMinLength = value.length >= 8;
  const hasUpperCase = /[A-Z]/.test(value);
  const hasLowerCase = /[a-z]/.test(value);
  const hasNumber = /\d/.test(value);
  const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(value);

  const isValid = hasMinLength && hasUpperCase && hasLowerCase && hasNumber;

  if (!isValid) {
    const errors = [];
    if (!hasMinLength) errors.push("at least 8 characters");
    if (!hasUpperCase) errors.push("one uppercase letter");
    if (!hasLowerCase) errors.push("one lowercase letter");
    if (!hasNumber) errors.push("one number");

    return {
      isValid: false,
      error: `Password must contain ${errors.join(", ")}`,
    };
  }

  return { isValid: true };
}

/**
 * Validate phone number
 */
export function phone(value: string): ValidationResult {
  if (!value) {
    return { isValid: true };
  }

  // Remove all non-digit characters
  const digits = value.replace(/\D/g, "");
  const isValid = digits.length === 10 || digits.length === 11;

  return {
    isValid,
    error: isValid ? undefined : "Please enter a valid phone number",
  };
}

/**
 * Validate URL
 */
export function url(value: string): ValidationResult {
  if (!value) {
    return { isValid: true };
  }

  try {
    new URL(value);
    return { isValid: true };
  } catch {
    return {
      isValid: false,
      error: "Please enter a valid URL",
    };
  }
}

/**
 * Validate date
 */
export function date(value: string): ValidationResult {
  if (!value) {
    return { isValid: true };
  }

  const dateObj = new Date(value);
  const isValid = !isNaN(dateObj.getTime());

  return {
    isValid,
    error: isValid ? undefined : "Please enter a valid date",
  };
}

/**
 * Validate number
 */
export function number(value: any): ValidationResult {
  if (value === null || value === undefined || value === "") {
    return { isValid: true };
  }

  const isValid = !isNaN(Number(value));

  return {
    isValid,
    error: isValid ? undefined : "Please enter a valid number",
  };
}

/**
 * Validate integer
 */
export function integer(value: any): ValidationResult {
  if (value === null || value === undefined || value === "") {
    return { isValid: true };
  }

  const num = Number(value);
  const isValid = !isNaN(num) && Number.isInteger(num);

  return {
    isValid,
    error: isValid ? undefined : "Please enter a valid integer",
  };
}

// ============================================
// ASYNC VALIDATORS
// ============================================

/**
 * Check if email is already taken (async)
 */
export async function emailAvailable(
  value: string,
  checkFunction: (email: string) => Promise<boolean>
): Promise<ValidationResult> {
  if (!value) {
    return { isValid: true };
  }

  try {
    const isAvailable = await checkFunction(value);
    return {
      isValid: isAvailable,
      error: isAvailable ? undefined : "This email is already taken",
    };
  } catch {
    return {
      isValid: false,
      error: "Unable to verify email availability",
    };
  }
}

/**
 * Check if username is already taken (async)
 */
export async function usernameAvailable(
  value: string,
  checkFunction: (username: string) => Promise<boolean>
): Promise<ValidationResult> {
  if (!value) {
    return { isValid: true };
  }

  try {
    const isAvailable = await checkFunction(value);
    return {
      isValid: isAvailable,
      error: isAvailable ? undefined : "This username is already taken",
    };
  } catch {
    return {
      isValid: false,
      error: "Unable to verify username availability",
    };
  }
}

// ============================================
// VALIDATION HELPERS
// ============================================

/**
 * Combine multiple validators
 */
export function combine(
  ...validators: ((value: any) => ValidationResult)[]
) {
  return (value: any): ValidationResult => {
    for (const validator of validators) {
      const result = validator(value);
      if (!result.isValid) {
        return result;
      }
    }
    return { isValid: true };
  };
}

/**
 * Validate an object with multiple fields
 */
export function validateForm<T extends Record<string, any>>(
  values: T,
  rules: Partial<Record<keyof T, (value: any) => ValidationResult>>
): { isValid: boolean; errors: Partial<Record<keyof T, string>> } {
  const errors: Partial<Record<keyof T, string>> = {};
  let isValid = true;

  for (const field in rules) {
    const validator = rules[field];
    if (validator) {
      const result = validator(values[field]);
      if (!result.isValid) {
        errors[field] = result.error;
        isValid = false;
      }
    }
  }

  return { isValid, errors };
}

/**
 * Validate a single field
 */
export function validateField(
  value: any,
  validators: ((value: any) => ValidationResult)[]
): ValidationResult {
  for (const validator of validators) {
    const result = validator(value);
    if (!result.isValid) {
      return result;
    }
  }
  return { isValid: true };
}

// ============================================
// CUSTOM VALIDATORS
// ============================================

/**
 * Create a custom validator
 */
export function custom(
  validate: (value: any) => boolean,
  message: string
) {
  return (value: any): ValidationResult => {
    const isValid = validate(value);
    return {
      isValid,
      error: isValid ? undefined : message,
    };
  };
}
