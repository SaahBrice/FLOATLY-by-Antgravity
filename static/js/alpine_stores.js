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
            nav_ai: { en: 'AI', fr: 'IA' },
            nav_pricing: { en: 'Pricing', fr: 'Tarifs' },
            nav_login: { en: 'Log In', fr: 'Connexion' },
            nav_signup: { en: 'Get Started', fr: 'Commencer' },

            // Hero Section
            hero_badge: { en: '🇨🇲 #1 Mobile Money Tracking App in Cameroon', fr: '🇨🇲 #1 Application de Suivi Mobile Money au Cameroun' },
            hero_title: { en: 'Track Your Float.', fr: 'Suivez Votre Float.' },
            hero_title2: { en: 'Grow Your Business.', fr: 'Développez Votre Business.' },
            hero_subtitle: { en: 'The AI-powered digital logbook for mobile money agents. Never lose a transaction again.', fr: 'Le carnet numérique alimenté par l\'IA pour les agents mobile money. Ne perdez plus jamais une transaction.' },
            hero_cta: { en: 'Start Free Today', fr: 'Commencer Gratuitement' },
            hero_cta2: { en: 'Watch Demo', fr: 'Voir la Démo' },
            hero_stat1: { en: 'Active Agents', fr: 'Agents Actifs' },
            hero_stat2: { en: 'CFA Tracked', fr: 'CFA Suivis' },
            hero_stat3: { en: 'Uptime', fr: 'Disponibilité' },

            // Features Section
            features_badge: { en: 'POWERFUL FEATURES', fr: 'FONCTIONNALITÉS PUISSANTES' },
            features_title: { en: 'Everything You Need to', fr: 'Tout ce qu\'il vous faut pour' },
            features_title2: { en: 'Dominate', fr: 'Dominer' },
            features_subtitle: { en: 'Say goodbye to paper cashbooks. Floatly gives you superpowers to track, analyze, and grow your mobile money business.', fr: 'Dites adieu aux cahiers papier. Floatly vous donne des super-pouvoirs pour suivre, analyser et développer votre business mobile money.' },

            // AI Smart Entry Feature
            feature_ai_title: { en: 'AI Smart Entry', fr: 'Saisie Intelligente IA' },
            feature_ai_desc: { en: 'Snap a photo of your MoMo/OM confirmation screen, or just speak! Describe your transaction naturally and our AI extracts everything. No typing required!', fr: 'Prenez une photo de votre écran de confirmation MoMo/OM, ou parlez simplement ! Décrivez votre transaction naturellement et notre IA extrait tout. Pas besoin de taper !' },
            feature_ai_photo: { en: '📷 Photo Capture', fr: '📷 Capture Photo' },
            feature_ai_voice: { en: '🎙️ Voice Input', fr: '🎙️ Saisie Vocale' },
            feature_ai_accuracy: { en: '99% Accuracy', fr: '99% de Précision' },
            feature_ai_offline: { en: 'Works Offline', fr: 'Fonctionne Hors Ligne' },

            // Other Features
            feature_multikiosk_title: { en: 'Multi-Kiosk Management', fr: 'Gestion Multi-Kiosques' },
            feature_multikiosk_desc: { en: 'Own 5 kiosks? 10? Manage them all from one dashboard. Switch between locations instantly.', fr: 'Vous avez 5 kiosques ? 10 ? Gérez-les tous depuis un seul tableau de bord. Changez de lieu instantanément.' },

            feature_fraud_title: { en: 'AI Fraud Detection', fr: 'Détection de Fraude IA' },
            feature_fraud_desc: { en: 'Get instant alerts for suspicious patterns: duplicate transactions, unusual amounts, or employee discrepancies.', fr: 'Recevez des alertes instantanées pour les activités suspectes : transactions en double, montants inhabituels ou écarts des employés.' },

            feature_storage_title: { en: 'Forever Data Storage', fr: 'Stockage Permanent' },
            feature_storage_desc: { en: 'Your data is stored securely for years. No more losing cashbooks to fire, water, or theft.', fr: 'Vos données sont stockées en sécurité pendant des années. Fini les pertes de cahiers à cause du feu, de l\'eau ou du vol.' },

            feature_search_title: { en: 'Comprehensive Search', fr: 'Recherche Complète' },
            feature_search_desc: { en: 'Customer asking about a transaction from 2 years ago? Find it in seconds. Search by phone, amount, date, or network.', fr: 'Un client demande une transaction d\'il y a 2 ans ? Trouvez-la en secondes. Recherchez par téléphone, montant, date ou réseau.' },

            feature_team_title: { en: 'Team & Cashier Access', fr: 'Accès Équipe & Caissiers' },
            feature_team_desc: { en: 'Invite your cashiers with controlled permissions. See who logged what and keep everyone accountable.', fr: 'Invitez vos caissiers avec des permissions contrôlées. Voyez qui a enregistré quoi et gardez tout le monde responsable.' },

            feature_referral_title: { en: 'Referral Bonus', fr: 'Bonus de Parrainage' },
            feature_referral_desc: { en: 'Invite fellow agents and earn rewards! Get 1,000 CFA for every agent who signs up with your code.', fr: 'Invitez d\'autres agents et gagnez des récompenses ! Recevez 1 000 CFA pour chaque agent inscrit avec votre code.' },

            feature_notifications_title: { en: 'Daily Smart Notifications', fr: 'Notifications Intelligentes' },
            feature_notifications_desc: { en: 'Get daily summaries, profit alerts, and AI-powered tips to improve your business.', fr: 'Recevez des résumés quotidiens, alertes de profit et conseils IA pour améliorer votre business.' },

            // How It Works Section
            how_badge: { en: 'EASY TO START', fr: 'FACILE À DÉMARRER' },
            how_title: { en: 'How It Works', fr: 'Comment Ça Marche' },
            step1_title: { en: 'Create Account', fr: 'Créer un Compte' },
            step1_desc: { en: 'Sign up in 30 seconds with just your phone number', fr: 'Inscrivez-vous en 30 secondes avec juste votre numéro' },
            step2_title: { en: 'Add Transactions', fr: 'Ajouter des Transactions' },
            step2_desc: { en: 'Log deposits & withdrawals by voice, photo, or typing', fr: 'Enregistrez dépôts et retraits par voix, photo ou saisie' },
            step3_title: { en: 'Track Profits', fr: 'Suivre les Profits' },
            step3_desc: { en: 'See your earnings and analytics in real-time', fr: 'Voyez vos gains et analyses en temps réel' },

            // AI Features Section
            ai_badge: { en: 'POWERED BY AI', fr: 'ALIMENTÉ PAR L\'IA' },
            ai_title: { en: 'AI That Works', fr: 'L\'IA Qui Travaille' },
            ai_title2: { en: 'For You', fr: 'Pour Vous' },
            ai_subtitle: { en: 'Floatly\'s AI doesn\'t just store data—it analyzes, predicts, and recommends.', fr: 'L\'IA de Floatly ne stocke pas seulement les données—elle analyse, prédit et recommande.' },

            ai_voice_title: { en: 'Voice Transaction Entry', fr: 'Saisie Vocale des Transactions' },
            ai_voice_desc: { en: 'Just speak naturally! Say "Orange Money withdrawal 75,000 to 690123456" and Floatly\'s AI understands everything.', fr: 'Parlez naturellement ! Dites "Retrait Orange Money 75 000 au 690123456" et l\'IA de Floatly comprend tout.' },
            ai_voice_1: { en: 'Natural language understanding', fr: 'Compréhension du langage naturel' },
            ai_voice_2: { en: 'French & English support', fr: 'Support Français & Anglais' },
            ai_voice_3: { en: 'Hands-free operation', fr: 'Utilisation mains libres' },

            ai_insights_title: { en: 'Smart Recommendations', fr: 'Recommandations Intelligentes' },
            ai_insights_desc: { en: 'Our AI analyzes your business patterns and sends personalized tips.', fr: 'Notre IA analyse vos habitudes et envoie des conseils personnalisés.' },
            ai_insights_tip: { en: 'Your Thursday afternoon deposits are 40% higher than average. Consider having extra float ready after 2 PM.', fr: 'Vos dépôts du jeudi après-midi sont 40% plus élevés que la moyenne. Prévoyez plus de float après 14h.' },

            ai_fraud_title: { en: 'Fraud Protection', fr: 'Protection Anti-Fraude' },
            ai_fraud_desc: { en: 'AI monitors every transaction for anomalies. Duplicate entries, unusual amounts, suspicious patterns—we catch them.', fr: 'L\'IA surveille chaque transaction. Doublons, montants inhabituels, activités suspectes—nous les détectons.' },
            ai_fraud_alert: { en: 'Transaction #4521 looks like a duplicate of #4518 from 3 minutes ago. Please verify.', fr: 'La transaction #4521 ressemble à un doublon de #4518 d\'il y a 3 minutes. Veuillez vérifier.' },

            // CTA Section
            cta_badge: { en: 'JOIN 2,500+ AGENTS', fr: 'REJOIGNEZ 2 500+ AGENTS' },
            cta_title: { en: 'Ready to Transform Your Business?', fr: 'Prêt à Transformer Votre Business ?' },
            cta_subtitle: { en: 'Stop losing transactions in paper cashbooks. Start tracking every CFA with AI-powered precision.', fr: 'Arrêtez de perdre des transactions dans les cahiers papier. Suivez chaque CFA avec la précision de l\'IA.' },
            cta_button: { en: 'Start Free Today', fr: 'Commencer Gratuitement' },
            cta_login: { en: 'Already have an account?', fr: 'Déjà un compte ?' },
            cta_secure: { en: 'Secure Data', fr: 'Données Sécurisées' },
            cta_support: { en: '24/7 Support', fr: 'Support 24/7' },
            cta_offline: { en: 'Works Offline', fr: 'Fonctionne Hors Ligne' },

            // Disclaimer
            disclaimer_title: { en: 'Your Digital Logbook, Nothing More', fr: 'Votre Carnet Numérique, Rien de Plus' },
            disclaimer_text: { en: 'Floatly is not affiliated with MTN, Orange, or any mobile money network. We don\'t process, hold, or transfer any money. We\'re simply the smartest way to record and track your transactions—like upgrading from a paper cashbook to an AI-powered digital one.', fr: 'Floatly n\'est affilié à aucun réseau mobile money (MTN, Orange, etc.). Nous ne traitons, détenons ni transférons d\'argent. Nous sommes simplement la façon la plus intelligente d\'enregistrer et suivre vos transactions—comme passer d\'un cahier papier à un carnet numérique alimenté par l\'IA.' },

            // Partners Section
            partners_badge: { en: '🤝 ECOSYSTEM', fr: '🤝 ÉCOSYSTÈME' },
            partners_title: { en: 'Built By', fr: 'Créé Par' },
            partners_subtitle: { en: 'Floatly is part of a family of African-built products empowering creativity, education, and technology across the continent.', fr: 'Floatly fait partie d\'une famille de produits africains qui promeuvent la créativité, l\'éducation et la technologie à travers le continent.' },
            partners_tagline: { en: '🌍 Building technology that matters, from Africa, for the world.', fr: '🌍 Construire une technologie qui compte, depuis l\'Afrique, pour le monde.' },

            // Footer
            footer_brand_desc: { en: 'The AI-powered digital logbook for mobile money agents in Cameroon. Track, analyze, and grow your business.', fr: 'Le carnet numérique alimenté par l\'IA pour les agents mobile money au Cameroun. Suivez, analysez et développez votre business.' },
            footer_product: { en: 'Product', fr: 'Produit' },
            footer_support: { en: 'Support', fr: 'Support' },
            footer_legal: { en: 'Legal', fr: 'Légal' },
            footer_help: { en: 'Help Center', fr: 'Centre d\'Aide' },
            footer_contact: { en: 'Contact', fr: 'Contact' },
            footer_privacy: { en: 'Privacy', fr: 'Confidentialité' },
            footer_terms: { en: 'Terms', fr: 'Conditions' },
            footer_copyright: { en: '© 2024 Floatly. Built for Cameroon\'s mobile money agents.', fr: '© 2024 Floatly. Conçu pour les agents mobile money du Cameroun.' },
            footer_made: { en: 'Made with ❤️ in 🇨🇲 Cameroon', fr: 'Fait avec ❤️ au 🇨🇲 Cameroun' },
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
