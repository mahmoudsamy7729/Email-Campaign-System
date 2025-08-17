from django.shortcuts import render

# Create your views here.
def index(request):
    return render(request, 'index.html')

def analytics(request):
    return render(request, 'analytics.html')

def finance(request):
    return render(request, 'finance.html')

def crypto(request):
    return render(request, 'crypto.html')


def charts(request):
    return render(request, 'charts.html')

def widgets(request):
    return render(request, 'widgets.html')

def font_icons(request):
    return render(request, 'font-icons.html')

def dragndrop(request):
    return render(request, 'dragndrop.html')

def tables(request):
    return render(request, 'tables.html')


def campaigns(request):
    return render(request, 'apps/campaigns.html')

def apps_mailbox(request):
    return render(request, 'apps/mailbox.html')

def apps_todolist(request):
    return render(request, 'apps/todolist.html')

def apps_notes(request):
    return render(request, 'apps/notes.html')

def apps_scrumboard(request):
    return render(request, 'apps/scrumboard.html')

def apps_contacts(request):
    return render(request, 'apps/contacts.html')

def apps_calendar(request):
    return render(request, 'apps/calendar.html')

def apps_invoice_add(request):
    return render(request, 'apps/invoice/add.html')

def apps_invoice_edit(request):
    return render(request, 'apps/invoice/edit.html')

def apps_invoice_list(request):
    return render(request, 'apps/invoice/list.html')

def apps_invoice_preview(request):
    return render(request, 'apps/invoice/preview.html')


def components_tabs(request):
    return render(request, 'ui-components/tabs.html')

def components_accordions(request):
    return render(request, 'ui-components/accordions.html')

def components_modals(request):
    return render(request, 'ui-components/modals.html')

def components_cards(request):
    return render(request, 'ui-components/cards.html')

def components_carousel(request):
    return render(request, 'ui-components/carousel.html')

def components_countdown(request):
    return render(request, 'ui-components/countdown.html')

def components_counter(request):
    return render(request, 'ui-components/counter.html')

def components_sweetalert(request):
    return render(request, 'ui-components/sweetalert.html')

def components_timeline(request):
    return render(request, 'ui-components/timeline.html')

def components_notifications(request):
    return render(request, 'ui-components/notifications.html')

def components_media_object(request):
    return render(request, 'ui-components/media-object.html')

def components_list_group(request):
    return render(request, 'ui-components/list-group.html')

def components_pricing_table(request):
    return render(request, 'ui-components/pricing-table.html')

def components_lightbox(request):
    return render(request, 'ui-components/lightbox.html')



def elements_alerts(request):
    return render(request, 'elements/alerts.html')

def elements_avatar(request):
    return render(request, 'elements/avatar.html')

def elements_badges(request):
    return render(request, 'elements/badges.html')

def elements_breadcrumbs(request):
    return render(request, 'elements/breadcrumbs.html')

def elements_buttons(request):
    return render(request, 'elements/buttons.html')

def elements_buttons_group(request):
    return render(request, 'elements/buttons-group.html')

def elements_color_library(request):
    return render(request, 'elements/color-library.html')

def elements_dropdown(request):
    return render(request, 'elements/dropdown.html')

def elements_infobox(request):
    return render(request, 'elements/infobox.html')

def elements_jumbotron(request):
    return render(request, 'elements/jumbotron.html')

def elements_loader(request):
    return render(request, 'elements/loader.html')

def elements_pagination(request):
    return render(request, 'elements/pagination.html')

def elements_popovers(request):
    return render(request, 'elements/popovers.html')

def elements_progress_bar(request):
    return render(request, 'elements/progress-bar.html')

def elements_search(request):
    return render(request, 'elements/search.html')

def elements_tooltips(request):
    return render(request, 'elements/tooltips.html')

def elements_treeview(request):
    return render(request, 'elements/treeview.html')

def elements_typography(request):
    return render(request, 'elements/typography.html')


def datatables_advanced(request):
    return render(request, 'datatables/advanced.html')

def datatables_alt_pagination(request):
    return render(request, 'datatables/alt-pagination.html')

def datatables_basic(request):
    return render(request, 'datatables/basic.html')

def datatables_order_sorting(request):
    return render(request, 'datatables/order-sorting.html')

def datatables_multi_column(request):
    return render(request, 'datatables/multi-column.html')

def datatables_multiple_tables(request):
    return render(request, 'datatables/multiple-tables.html')

def datatables_checkbox(request):
    return render(request, 'datatables/checkbox.html')

def datatables_clone_header(request):
    return render(request, 'datatables/clone-header.html')

def datatables_column_chooser(request):
    return render(request, 'datatables/column-chooser.html')

def datatables_range_search(request):
    return render(request, 'datatables/range-search.html')

def datatables_export(request):
    return render(request, 'datatables/export.html')

def datatables_skin(request):
    return render(request, 'datatables/skin.html')

def datatables_sticky_header(request):
    return render(request, 'datatables/sticky-header.html')


def forms_basic(request):
    return render(request, 'forms/basic.html')

def forms_input_group(request):
    return render(request, 'forms/input-group.html')

def forms_layouts(request):
    return render(request, 'forms/layouts.html')

def forms_validation(request):
    return render(request, 'forms/validation.html')

def forms_input_mask(request):
    return render(request, 'forms/input-mask.html')

def forms_select2(request):
    return render(request, 'forms/select2.html')

def forms_touchspin(request):
    return render(request, 'forms/touchspin.html')

def forms_checkbox_radio(request):
    return render(request, 'forms/checkbox-radio.html')

def forms_switches(request):
    return render(request, 'forms/switches.html')

def forms_wizards(request):
    return render(request, 'forms/wizards.html')

def forms_file_upload(request):
    return render(request, 'forms/file-upload.html')

def forms_quill_editor(request):
    return render(request, 'forms/quill-editor.html')

def forms_markdown_editor(request):
    return render(request, 'forms/markdown-editor.html')

def forms_date_picker(request):
    return render(request, 'forms/date-picker.html')

def forms_clipboard(request):
    return render(request, 'forms/clipboard.html')


    
def pages_knowledge_base(request):
    return render(request, 'pages/knowledge-base.html')

def pages_faq(request):
    return render(request, 'pages/faq.html')

def pages_contact_us(request):
    return render(request, 'pages/contact-us.html')

def pages_coming_soon(request):
    return render(request, 'pages/coming-soon.html')

def pages_error404(request):
    return render(request, 'pages/error404.html')

def pages_error500(request):
    return render(request, 'pages/error500.html')

def pages_error503(request):
    return render(request, 'pages/error503.html')

def pages_maintenence(request):
    return render(request, 'pages/maintenence.html')



def users_profile(request):
    return render(request, 'users/profile.html')

def users_user_account_settings(request):
    return render(request, 'users/user-account-settings.html')



def auth_boxed_signin(request):
    return render(request, 'auth/boxed-signin.html')

def auth_boxed_signup(request):
    return render(request, 'auth/boxed-signup.html')

def auth_boxed_lockscreen(request):
    return render(request, 'auth/boxed-lockscreen.html')

def auth_boxed_password_reset(request):
    return render(request, 'auth/boxed-password-reset.html')

def auth_cover_login(request):
    return render(request, 'auth/cover-login.html')

def auth_cover_register(request):
    return render(request, 'auth/cover-register.html')

def auth_cover_lockscreen(request):
    return render(request, 'auth/cover-lockscreen.html')

def auth_cover_password_reset(request):
    return render(request, 'auth/cover-password-reset.html')
