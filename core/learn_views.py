"""
Learn views for educational content.

Public, SEO-friendly pages for mobile money agent education.
"""

from django.views.generic import TemplateView


# Chapter data structure for reuse
CHAPTERS = [
    {
        'slug': 'safety-tips',
        'title': 'Safety Tips for Mobile Money Agents',
        'short_title': 'Safety Tips',
        'icon': '🛡️',
        'color': 'green',
        'summary': 'Essential security practices to protect yourself and your customers.',
        'order': 1,
    },
    {
        'slug': 'avoid-scammers',
        'title': 'How to Recognize and Avoid Scammers',
        'short_title': 'Avoid Scammers',
        'icon': '⚠️',
        'color': 'red',
        'summary': 'Learn the common scam tactics and how to protect your business.',
        'order': 2,
    },
    {
        'slug': 'best-practices',
        'title': 'Daily Operations Best Practices',
        'short_title': 'Best Practices',
        'icon': '✨',
        'color': 'blue',
        'summary': 'Run your kiosk efficiently with proven strategies.',
        'order': 3,
    },
    {
        'slug': 'register-as-agent',
        'title': 'How to Register as a Professional Agent',
        'short_title': 'Register as Agent',
        'icon': '📋',
        'color': 'purple',
        'summary': 'Step-by-step guide to becoming a registered mobile money agent.',
        'order': 4,
    },
    {
        'slug': 'why-go-pro',
        'title': 'Benefits of Being a Professional Agent',
        'short_title': 'Why Go Pro',
        'icon': '🚀',
        'color': 'orange',
        'summary': 'Discover why registration and professionalism pay off.',
        'order': 5,
    },
    {
        'slug': 'record-keeping',
        'title': 'Why Accurate Record Keeping Matters',
        'short_title': 'Record Keeping',
        'icon': '📊',
        'color': 'cyan',
        'summary': 'Master the art of tracking transactions for success.',
        'order': 6,
    },
]


def get_chapter_by_slug(slug):
    """Get chapter data by slug."""
    for chapter in CHAPTERS:
        if chapter['slug'] == slug:
            return chapter
    return None


def get_chapter_navigation(slug):
    """Get previous and next chapters for navigation."""
    for i, chapter in enumerate(CHAPTERS):
        if chapter['slug'] == slug:
            prev_chapter = CHAPTERS[i - 1] if i > 0 else None
            next_chapter = CHAPTERS[i + 1] if i < len(CHAPTERS) - 1 else None
            return prev_chapter, next_chapter
    return None, None


class LearnIndexView(TemplateView):
    """
    Public index page for all educational chapters.
    SEO-optimized with schema.org markup.
    """
    template_name = 'learn/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['chapters'] = CHAPTERS
        context['page_title'] = 'Learn: Mobile Money Agent Guide'
        context['page_description'] = 'Free educational resources for mobile money agents in Cameroon. Learn safety tips, avoid scams, and master best practices.'
        return context


class ChapterDetailView(TemplateView):
    """
    Individual chapter detail page.
    Template is determined by chapter slug.
    """
    
    def get_template_names(self):
        slug = self.kwargs.get('slug', '')
        return [f'learn/chapters/{slug}.html']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs.get('slug', '')
        
        chapter = get_chapter_by_slug(slug)
        if chapter:
            context['chapter'] = chapter
            context['page_title'] = chapter['title']
            context['page_description'] = chapter['summary']
            
            prev_ch, next_ch = get_chapter_navigation(slug)
            context['prev_chapter'] = prev_ch
            context['next_chapter'] = next_ch
            context['chapters'] = CHAPTERS
        
        return context


# For dashboard modal - returns chapter list as JSON-friendly context
class LearnModalDataView(TemplateView):
    """Returns learn modal partial for dashboard."""
    template_name = 'learn/partials/modal_content.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['chapters'] = CHAPTERS
        return context
