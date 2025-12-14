/**
 * Alpine.js Stores for Floatly
 * 
 * Theme and i18n (internationalization) stores
 */

// Initialize theme before Alpine loads (prevents flash)
(function () {
    const theme = localStorage.getItem('floatly_theme') || 'dark';
    if (theme === 'dark') {
        document.documentElement.classList.add('dark');
    } else {
        document.documentElement.classList.remove('dark');
    }
})();

// Alpine stores - initialized after Alpine loads
document.addEventListener('alpine:init', () => {
    // Theme Store (dark/light mode)
    Alpine.store('theme', {
        mode: localStorage.getItem('floatly_theme') || 'dark',

        get isDark() {
            return this.mode === 'dark';
        },

        toggle() {
            this.mode = this.mode === 'dark' ? 'light' : 'dark';
            localStorage.setItem('floatly_theme', this.mode);
            document.documentElement.classList.toggle('dark', this.mode === 'dark');
        },

        set(mode) {
            this.mode = mode;
            localStorage.setItem('floatly_theme', mode);
            document.documentElement.classList.toggle('dark', mode === 'dark');
        }
    });

    // i18n Store (French/English translations)
    Alpine.store('i18n', {
        lang: localStorage.getItem('floatly_lang') || 'fr',

        translations: {
            // Navigation
            nav_features: { en: 'Features', fr: 'Fonctionnalités' },
            nav_pricing: { en: 'Pricing', fr: 'Tarifs' },
            nav_login: { en: 'Log In', fr: 'Connexion' },
            nav_signup: { en: 'Get Started', fr: 'Commencer' },

            // Hero
            hero_title: { en: 'Track Your Float.', fr: 'Suivez Votre Float.' },
            hero_title2: { en: 'Grow Your Business.', fr: 'Développez Votre Business.' },
            hero_subtitle: { en: 'The digital logbook for mobile money agents in Cameroon', fr: 'Le carnet numérique pour les agents mobile money au Cameroun' },
            hero_cta: { en: 'Start Free', fr: 'Commencer Gratuit' },
            hero_cta2: { en: 'Watch Demo', fr: 'Voir la Démo' },

            // Features
            features_title: { en: 'Built for Mobile Money Agents', fr: 'Conçu pour les Agents Mobile Money' },
            features_subtitle: { en: 'Everything you need to manage your kiosk and track profits', fr: 'Tout ce dont vous avez besoin pour gérer votre kiosque et suivre vos profits' },

            feature1_title: { en: 'Auto Profit Calculator', fr: 'Calcul Automatique des Profits' },
            feature1_desc: { en: 'Automatic commission calculation based on official rates', fr: 'Calcul automatique des commissions basé sur les tarifs officiels' },

            feature2_title: { en: 'Multi-Kiosk Management', fr: 'Gestion Multi-Kiosques' },
            feature2_desc: { en: 'Manage multiple locations from one account', fr: 'Gérez plusieurs points de vente depuis un seul compte' },

            feature3_title: { en: 'Works Offline', fr: 'Fonctionne Hors Ligne' },
            feature3_desc: { en: 'No internet? No problem. Sync when back online', fr: 'Pas d\'internet? Pas de problème. Synchronisez une fois en ligne' },

            feature4_title: { en: 'Team Access', fr: 'Accès Équipe' },
            feature4_desc: { en: 'Invite cashiers with controlled permissions', fr: 'Invitez vos caissiers avec des permissions contrôlées' },

            // How it works
            how_title: { en: 'How It Works', fr: 'Comment Ça Marche' },
            step1_title: { en: 'Create Account', fr: 'Créer un Compte' },
            step1_desc: { en: 'Sign up in 30 seconds', fr: 'Inscrivez-vous en 30 secondes' },
            step2_title: { en: 'Add Transactions', fr: 'Ajouter des Transactions' },
            step2_desc: { en: 'Log deposits & withdrawals', fr: 'Enregistrez dépôts et retraits' },
            step3_title: { en: 'Track Profits', fr: 'Suivre les Profits' },
            step3_desc: { en: 'See your earnings in real-time', fr: 'Voyez vos gains en temps réel' },

            // CTA
            cta_title: { en: 'Ready to Simplify Your Business?', fr: 'Prêt à Simplifier Votre Business?' },
            cta_subtitle: { en: 'Join hundreds of agents already using Floatly', fr: 'Rejoignez des centaines d\'agents qui utilisent déjà Floatly' },
            cta_button: { en: 'Get Started Free', fr: 'Commencer Gratuitement' },
            cta_login: { en: 'Already have an account?', fr: 'Déjà un compte?' },

            // Footer
            footer_copyright: { en: '© 2024 Floatly. Built for Cameroon\'s mobile money agents.', fr: '© 2024 Floatly. Conçu pour les agents mobile money du Cameroun.' },
            footer_privacy: { en: 'Privacy', fr: 'Confidentialité' },
            footer_terms: { en: 'Terms', fr: 'Conditions' },

            // Pills
            pill_mtn: { en: 'MTN MoMo', fr: 'MTN MoMo' },
            pill_orange: { en: 'Orange Money', fr: 'Orange Money' },
            pill_offline: { en: 'Works Offline', fr: 'Hors Ligne' },
        },

        t(key) {
            const translation = this.translations[key];
            if (!translation) return key;
            return translation[this.lang] || translation['en'] || key;
        },

        setLang(lang) {
            this.lang = lang;
            localStorage.setItem('floatly_lang', lang);
        }
    });
});
