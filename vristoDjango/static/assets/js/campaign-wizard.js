    document.addEventListener('alpine:init', () => {
        // shared store for step navigation
        
        Alpine.store('wizard', {
            activeTab: 1,
            goTo(step) {
                if (step < this.activeTab) { this.activeTab = step; return; }
                // forward requires validation of current step
                const ok = Alpine.store('formCtl').validateStep(this.activeTab);
                if (ok) this.activeTab = step;
            },
            next() { this.goTo(this.activeTab + 1); },
            prev() { this.activeTab = Math.max(1, this.activeTab - 1); },
        });

        // controller store (so header can trigger validation)
        Alpine.store('formCtl', {
            validateStep(step) { return true; },
        });

        Alpine.data('form', () => ({
            // --- statusVal.toLowerCase
            activeTab: 1,
            submitting: false,
            audiences: [],
            statusOptions: ['draft','scheduled','sending','completed'],
            kindOptions: ["regular","automated","rss"],
            params: {
                id: (new URLSearchParams(location.search)).get('id') || '',
                title: '',
                kind: '',
                status: '',
                subject_line: '', 
                preview_text: '',
                from_name: '',
                from_email: '',
                reply_to: '',
                to_name_format: '',
                audience: '',
                estimated_recipients: 0,
                exclude_unsubscribed: true,
                schedule_type: '',
                scheduled_at: '',
                content_html: '',
            },
            errors: { title: '', subject: '', from_email: '', from_name: '', audience: '', scheduled_at: '', content_html: '' },
            EasyMDE: null,
            openTestModal: false,
            testEmail: '',
            testError: '',
            submittingTest: false,
            formatDateTimeForInput(dateString) {
                if (!dateString) return '';
                let d = new Date(dateString);
                return d.toISOString().slice(0,16); // "YYYY-MM-DDTHH:MM"
            },
            init() {
                // link store validator to this component
                Alpine.store('formCtl').validateStep = (s) => this.validateStep(s);
                this.loadData().then(() => {
                    this.initEasyMDE();
                });
                this.loadAudiences();
            },
            initEasyMDE(){
                this.EasyMDE = new EasyMDE({
                    element: document.getElementById('mde-autosave'),
                    
                });
            },
            async loadData(){
                let baseUrl = `${APP_URL}/campaigns/`;
                let campaignId = this.params.id;
                try {
                    let response = await fetch(`${baseUrl}${campaignId}/`);
                    if (!response.ok) throw new Error('Failed to load campaign data');
                    let data = await response.json();
                    this.params = { ...this.params, ...data };
                    if(this.params.scheduled_at != null){
                        this.params.scheduled_at = this.formatDateTimeForInput(data.scheduled_at);
                    }
                } catch (error) {
                    console.error(error);
                }
            },
            async saveAndExit(){
                this.params.content_html = this.EasyMDE.value();                
                try {
                    // Example payload
                    const payload = { ...this.params };

                    console.log(payload)
                    let response = await fetch(`${APP_URL}/campaigns/${this.params.id}/`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie("csrftoken"),
                        },
                        body: JSON.stringify(payload)
                        
                    });
                    let data = await response.json();
                    }catch(e){
                        console.error(e.message || "Unexpected error!");

                    }finally{
                        window.location.href = '/campaigns';
                    }

            },
            async sendTestEmail(){
                this.params.content_html = this.EasyMDE.value();
                if (!this.validateStep(1) || !this.validateStep(2) || !this.validateStep(3)) {
                    return;
                }
                this.testError = '';
                if (!this.testEmail || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.testEmail)) {
                    this.testError = 'Please enter a valid email address.';
                    return;
                }
                try {
                    const payload = {
                        email: this.testEmail,
                    };
                    this.submittingTest = true;

                    await fetch(`${APP_URL}/campaigns/${this.params.id}/test-email/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie("csrftoken"),
                        },
                        body: JSON.stringify(payload)
                    });
                    this.openTestModal = false;

                } catch (error) {
                    console.error('Error sending test email:', error);
                } finally {
                    this.openTestModal = false;
                }
            },

            // --- helpers
            validateField(key) {
                const v = this.params[key];
                this.errors[key] = '';
                if (['title','subject_line','from_email','from_name','status','kind'].includes(key) && !v) this.errors[key] = 'Required';
                if ((key === 'from_email' || key === 'reply_to') && v && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) this.errors[key] = 'Invalid email';
                if (key === 'audience' && !v) this.errors[key] = 'Please choose an audience';
                if (key === 'scheduled_at' && this.params.schedule_type === 'scheduled' && !v) this.errors[key] = 'Choose date & time';
                if (key === 'content_html' && !v) this.errors[key] = 'Content is required';
                return !this.errors[key];
            },
            validateStep(step) {
                if (step === 1) {
                    return ['title','subject','from_email','from_name','status','kind'].every(k => this.validateField(k));
                }
                if (step === 2) {
                    const okA = this.validateField('audience');
                    const okS = this.params.schedule_type === 'scheduled' ? this.validateField('scheduled_at') : true;
                    if (okA) this.estimateRecipients();
                    return okA && okS;
                }
                if (step === 3) {
                    return this.validateField('content_html');
                }
                return true;
            },
            audienceName(id) {
                const a = this.audiences.find(x => String(x.id) === String(id));
                return a ? a.name : '';
            },

            // --- data loaders
            loadAudiences() {
                if(this.audiences.length > 0){
                    return;
                }
                fetch(`${APP_URL}/audiences/`)
                .then(response => response.json())
                .then(data => {
                    this.audiences = data;
                })
                .catch(error => {
                    console.error('Error fetching audiences:', error);
                });
            },
            estimateRecipients() {
                // Stub: in real app call backend to compute estimate
                // e.g., GET /api/campaigns/estimate?audience=<id>&exclude_unsubscribed=<bool>
                // Here we just show a static example number
                this.estimatedRecipients = this.params.audience ? '~ 12,450' : '—';
            },

            // --- submit
            async submitForm() {
                this.params.content_html = this.EasyMDE.value();
                if (!this.validateStep(1) || !this.validateStep(2) || !this.validateStep(3)) {
                    return;
                }
                this.submitting = true;
                try {
                    // Example payload
                    const payload = { ...this.params };
                    let response = await fetch(`${APP_URL}/campaigns/${this.params.id}/send/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie("csrftoken"),
                        },
                        body: JSON.stringify(payload)
                    });
                    let data = await response.json();
                    }catch(e){
                        console.error(e.message || "Unexpected error!");

                    }finally{
                        this.submitting = false
                        this.params.status = 'sending';
                    }
            },
        }));
    });
