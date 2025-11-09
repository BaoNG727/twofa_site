// TinyMCE Initialization for VOZ Forum

document.addEventListener('DOMContentLoaded', function() {
    const textareas = document.querySelectorAll('textarea[name="content"]');
    
    if (textareas.length > 0 && typeof tinymce !== 'undefined') {
        tinymce.init({
            selector: 'textarea[name="content"]',
            height: 400,
            menubar: false,
            plugins: [
                'advlist', 'autolink', 'lists', 'link', 'image', 'charmap', 'preview',
                'anchor', 'searchreplace', 'visualblocks', 'code', 'fullscreen',
                'insertdatetime', 'media', 'table', 'help', 'wordcount', 'emoticons'
            ],
            toolbar: 'undo redo | formatselect | ' +
                'bold italic underline strikethrough | forecolor backcolor | ' +
                'alignleft aligncenter alignright alignjustify | ' +
                'bullist numlist outdent indent | ' +
                'link image media | emoticons | ' +
                'removeformat | code fullscreen',
            content_style: 'body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; font-size: 14px; line-height: 1.6; }',
            skin: 'oxide',
            content_css: 'default',
            language: 'vi',
            branding: false,
            promotion: false,
            
            // Image upload handler
            images_upload_handler: function (blobInfo, success, failure) {
                // For now, convert to base64
                const reader = new FileReader();
                reader.readAsDataURL(blobInfo.blob());
                reader.onloadend = function() {
                    success(reader.result);
                };
            },
            
            // Auto-resize
            auto_resize: true,
            min_height: 300,
            max_height: 800,
            
            // Paste options
            paste_as_text: false,
            paste_data_images: true,
            
            // Link options
            link_assume_external_targets: true,
            link_target_list: false,
            default_link_target: '_blank',
            
            // Setup callback
            setup: function(editor) {
                editor.on('init', function() {
                    console.log('TinyMCE initialized');
                });
            }
        });
    }
});

// Simple markdown support (toggle between editor modes)
function toggleMarkdownMode() {
    const editor = tinymce.activeEditor;
    if (editor) {
        const currentContent = editor.getContent();
        const textarea = document.querySelector('textarea[name="content"]');
        
        if (textarea.dataset.mode === 'markdown') {
            // Switch to rich text
            tinymce.init({selector: 'textarea[name="content"]'});
            textarea.dataset.mode = 'rich';
        } else {
            // Switch to markdown
            tinymce.remove();
            textarea.dataset.mode = 'markdown';
        }
    }
}
