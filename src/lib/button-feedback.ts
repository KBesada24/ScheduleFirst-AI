/**
 * Button Feedback Utilities
 * 
 * Consistent visual feedback for button interactions
 */

/**
 * Button state classes for consistent styling
 */
export const buttonStateClasses = {
  hover: "hover:shadow-md hover:scale-105 transition-all duration-200",
  active: "active:scale-95 active:shadow-sm",
  focus: "focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500",
  disabled: "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100",
  loading: "cursor-wait opacity-75",
};

/**
 * Ripple effect for button clicks
 */
export function createRippleEffect(event: React.MouseEvent<HTMLElement>) {
  const button = event.currentTarget;
  const ripple = document.createElement("span");
  
  const diameter = Math.max(button.clientWidth, button.clientHeight);
  const radius = diameter / 2;
  
  const rect = button.getBoundingClientRect();
  ripple.style.width = ripple.style.height = `${diameter}px`;
  ripple.style.left = `${event.clientX - rect.left - radius}px`;
  ripple.style.top = `${event.clientY - rect.top - radius}px`;
  ripple.classList.add("ripple");
  
  const existingRipple = button.getElementsByClassName("ripple")[0];
  if (existingRipple) {
    existingRipple.remove();
  }
  
  button.appendChild(ripple);
  
  setTimeout(() => {
    ripple.remove();
  }, 600);
}

/**
 * Add ripple effect styles to document
 */
export function addRippleStyles() {
  if (document.getElementById("ripple-styles")) return;
  
  const style = document.createElement("style");
  style.id = "ripple-styles";
  style.textContent = `
    .ripple {
      position: absolute;
      border-radius: 50%;
      background-color: rgba(255, 255, 255, 0.6);
      transform: scale(0);
      animation: ripple-animation 600ms ease-out;
      pointer-events: none;
    }
    
    @keyframes ripple-animation {
      to {
        transform: scale(4);
        opacity: 0;
      }
    }
  `;
  
  document.head.appendChild(style);
}

/**
 * Haptic feedback for mobile devices
 */
export function triggerHapticFeedback(type: "light" | "medium" | "heavy" = "light") {
  if ("vibrate" in navigator) {
    const duration = type === "light" ? 10 : type === "medium" ? 20 : 30;
    navigator.vibrate(duration);
  }
}

/**
 * Visual feedback for successful action
 */
export function showSuccessFeedback(element: HTMLElement) {
  element.classList.add("animate-pulse");
  element.style.backgroundColor = "rgb(34, 197, 94)"; // green-500
  
  setTimeout(() => {
    element.classList.remove("animate-pulse");
    element.style.backgroundColor = "";
  }, 500);
}

/**
 * Visual feedback for error action
 */
export function showErrorFeedback(element: HTMLElement) {
  element.classList.add("animate-shake");
  element.style.backgroundColor = "rgb(239, 68, 68)"; // red-500
  
  setTimeout(() => {
    element.classList.remove("animate-shake");
    element.style.backgroundColor = "";
  }, 500);
}

/**
 * Add shake animation styles
 */
export function addShakeStyles() {
  if (document.getElementById("shake-styles")) return;
  
  const style = document.createElement("style");
  style.id = "shake-styles";
  style.textContent = `
    @keyframes shake {
      0%, 100% { transform: translateX(0); }
      10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
      20%, 40%, 60%, 80% { transform: translateX(5px); }
    }
    
    .animate-shake {
      animation: shake 0.5s ease-in-out;
    }
  `;
  
  document.head.appendChild(style);
}

/**
 * Initialize all feedback styles
 */
export function initializeFeedbackStyles() {
  addRippleStyles();
  addShakeStyles();
}
