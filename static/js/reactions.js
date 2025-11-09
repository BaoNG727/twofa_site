// Reaction System for VOZ Forum

document.addEventListener('DOMContentLoaded', function() {
    // Handle reaction button clicks
    document.querySelectorAll('.reaction-btn').forEach(button => {
        button.addEventListener('click', async function(e) {
            e.preventDefault();
            
            const postId = this.dataset.postId;
            const reactionType = this.dataset.reactionType;
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            
            try {
                const response = await fetch(`/forum/post/${postId}/react/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-CSRFToken': csrfToken
                    },
                    body: `reaction_type=${reactionType}`
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    // Update reaction counts display
                    updateReactionCounts(postId, data.reaction_counts);
                    
                    // Toggle active state
                    const allButtons = document.querySelectorAll(`.reaction-btn[data-post-id="${postId}"]`);
                    allButtons.forEach(btn => btn.classList.remove('active'));
                    
                    if (data.action !== 'removed') {
                        this.classList.add('active');
                    }
                    
                    // Show toast notification
                    if (window.UXImprovements && window.UXImprovements.showToast) {
                        const messages = {
                            'added': 'Đã thêm reaction',
                            'removed': 'Đã bỏ reaction',
                            'changed': 'Đã đổi reaction'
                        };
                        window.UXImprovements.showToast(messages[data.action], 'success');
                    }
                }
            } catch (error) {
                console.error('Error toggling reaction:', error);
                if (window.UXImprovements && window.UXImprovements.showToast) {
                    window.UXImprovements.showToast('Có lỗi xảy ra', 'error');
                }
            }
        });
    });
});

function updateReactionCounts(postId, reactionCounts) {
    const container = document.querySelector(`.reaction-counts[data-post-id="${postId}"]`);
    if (!container) return;
    
    // Clear existing counts
    container.innerHTML = '';
    
    // Add updated counts
    const reactionEmojis = {
        'like': '👍',
        'love': '❤️',
        'laugh': '😂',
        'angry': '😠',
        'sad': '😢'
    };
    
    for (const [type, count] of Object.entries(reactionCounts)) {
        if (count > 0) {
            const span = document.createElement('span');
            span.className = 'reaction-count';
            span.innerHTML = `${reactionEmojis[type]} ${count}`;
            container.appendChild(span);
        }
    }
}

// Auto-update notification count
async function updateNotificationCount() {
    try {
        const response = await fetch('/forum/notifications/count/');
        const data = await response.json();
        
        const badge = document.querySelector('.notification-badge');
        if (badge) {
            if (data.count > 0) {
                badge.textContent = data.count > 99 ? '99+' : data.count;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        }
    } catch (error) {
        console.error('Error fetching notification count:', error);
    }
}

// Update notification count every 30 seconds
if (document.querySelector('.notification-badge')) {
    setInterval(updateNotificationCount, 30000);
    updateNotificationCount(); // Initial load
}
