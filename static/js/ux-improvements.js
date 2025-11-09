// ========================================
// Toast Notification System
// ========================================
class ToastManager {
    constructor() {
        this.container = null;
        this.init();
    }

    init() {
        // Create toast container
        this.container = document.createElement('div');
        this.container.className = 'toast-container';
        document.body.appendChild(this.container);
    }

    show(message, type = 'info', duration = 4000) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };
        
        toast.innerHTML = `
            <div class="toast-icon">${icons[type]}</div>
            <div class="toast-content">
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close" onclick="this.parentElement.remove()">×</button>
        `;
        
        this.container.appendChild(toast);
        
        // Auto remove after duration
        if (duration > 0) {
            setTimeout(() => {
                toast.classList.add('removing');
                setTimeout(() => toast.remove(), 300);
            }, duration);
        }
        
        return toast;
    }

    success(message, duration) {
        return this.show(message, 'success', duration);
    }

    error(message, duration) {
        return this.show(message, 'error', duration);
    }

    warning(message, duration) {
        return this.show(message, 'warning', duration);
    }

    info(message, duration) {
        return this.show(message, 'info', duration);
    }
}

// Global toast instance
const toast = new ToastManager();

// ========================================
// Loading Overlay
// ========================================
class LoadingOverlay {
    constructor() {
        this.overlay = null;
    }

    show(message = 'Đang tải...') {
        if (this.overlay) return;
        
        this.overlay = document.createElement('div');
        this.overlay.className = 'loading-overlay';
        this.overlay.innerHTML = `
            <div class="loading-overlay-content">
                <div class="loading-overlay-spinner"></div>
                <div class="loading-overlay-text">${message}</div>
            </div>
        `;
        
        document.body.appendChild(this.overlay);
        document.body.style.overflow = 'hidden';
    }

    hide() {
        if (this.overlay) {
            this.overlay.remove();
            this.overlay = null;
            document.body.style.overflow = '';
        }
    }
}

const loading = new LoadingOverlay();

// ========================================
// Modal Manager
// ========================================
class Modal {
    constructor() {
        this.overlay = null;
    }

    show(title, content, actions = []) {
        this.hide(); // Hide existing modal
        
        this.overlay = document.createElement('div');
        this.overlay.className = 'modal-overlay';
        
        const actionsHTML = actions.map(action => 
            `<button class="btn-${action.type || 'primary'}" onclick="${action.onclick}">${action.text}</button>`
        ).join('');
        
        this.overlay.innerHTML = `
            <div class="modal">
                <div class="modal-header">
                    <h3 class="modal-title">${title}</h3>
                    <button class="modal-close" onclick="modal.hide()">×</button>
                </div>
                <div class="modal-body">
                    ${content}
                </div>
                ${actions.length ? `<div class="modal-footer">${actionsHTML}</div>` : ''}
            </div>
        `;
        
        document.body.appendChild(this.overlay);
        document.body.style.overflow = 'hidden';
        
        // Activate with animation
        setTimeout(() => this.overlay.classList.add('active'), 10);
        
        // Close on overlay click
        this.overlay.addEventListener('click', (e) => {
            if (e.target === this.overlay) {
                this.hide();
            }
        });
        
        // Close on ESC key
        this.escHandler = (e) => {
            if (e.key === 'Escape') this.hide();
        };
        document.addEventListener('keydown', this.escHandler);
    }

    hide() {
        if (this.overlay) {
            this.overlay.classList.remove('active');
            setTimeout(() => {
                this.overlay.remove();
                this.overlay = null;
                document.body.style.overflow = '';
            }, 300);
            
            if (this.escHandler) {
                document.removeEventListener('keydown', this.escHandler);
            }
        }
    }

    confirm(title, message, onConfirm) {
        this.show(title, `<p>${message}</p>`, [
            {
                text: 'Hủy',
                type: 'login',
                onclick: 'modal.hide()'
            },
            {
                text: 'Xác nhận',
                type: 'register',
                onclick: `modal.hide(); (${onConfirm.toString()})()`
            }
        ]);
    }
}

const modal = new Modal();

// ========================================
// Progress Bar
// ========================================
class ProgressBar {
    constructor() {
        this.bar = document.createElement('div');
        this.bar.className = 'progress-bar';
        document.body.appendChild(this.bar);
    }

    start() {
        this.bar.style.width = '0%';
        setTimeout(() => this.bar.style.width = '30%', 10);
    }

    progress(percent) {
        this.bar.style.width = `${percent}%`;
    }

    complete() {
        this.bar.style.width = '100%';
        setTimeout(() => this.bar.style.width = '0%', 300);
    }
}

const progressBar = new ProgressBar();

// ========================================
// Form Enhancement
// ========================================
function enhanceForms() {
    // Add loading state to form submissions
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = this.querySelector('button[type="submit"], input[type="submit"]');
            if (submitBtn && !submitBtn.classList.contains('btn-loading')) {
                submitBtn.classList.add('btn-loading');
                submitBtn.disabled = true;
            }
        });
    });
}

// ========================================
// Skeleton Loading Helper
// ========================================
function createSkeleton(count = 3) {
    let html = '';
    for (let i = 0; i < count; i++) {
        html += `
            <div class="skeleton-card">
                <div class="skeleton-header">
                    <div class="skeleton skeleton-avatar"></div>
                    <div class="skeleton-content">
                        <div class="skeleton skeleton-title"></div>
                        <div class="skeleton skeleton-text"></div>
                    </div>
                </div>
                <div class="skeleton skeleton-body"></div>
                <div class="skeleton-footer">
                    <div class="skeleton skeleton-tag"></div>
                    <div class="skeleton skeleton-tag"></div>
                </div>
            </div>
        `;
    }
    return html;
}

// ========================================
// Smooth Scroll
// ========================================
function smoothScrollTo(element) {
    element.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
    });
}

// ========================================
// Initialize on page load
// ========================================
document.addEventListener('DOMContentLoaded', function() {
    enhanceForms();
    
    // Show Django messages as toasts
    const djangoMessages = document.querySelectorAll('.messages .alert, .messages li');
    djangoMessages.forEach(msg => {
        const text = msg.textContent.trim();
        const type = msg.classList.contains('success') ? 'success' :
                    msg.classList.contains('error') ? 'error' :
                    msg.classList.contains('warning') ? 'warning' : 'info';
        
        toast.show(text, type);
        msg.style.display = 'none';
    });
});

// ========================================
// Export for global use
// ========================================
window.toast = toast;
window.loading = loading;
window.modal = modal;
window.progressBar = progressBar;
window.createSkeleton = createSkeleton;
window.smoothScrollTo = smoothScrollTo;
