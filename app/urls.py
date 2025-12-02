# app/urls.py

from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("", views.user_login, name="login"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path(
        "api/paper/<int:paper_id>/deactivate/",
        views.deactivate_paper,
        name="deactivate_paper",
    ),
    path("logout/", views.user_logout, name="logout"),
    path("register/", views.user_register, name="register"),
    path(
        "password_reset/",
        views.password_reset_request, 
        name="password_reset",
    ),
    
    path(
        "password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    path("generate/", views.generate_questions, name="generate_questions"),
    path("home/", views.home, name="home"),
    path("save-paper/", views.save_paper, name="save_paper"),
    path("papers/", views.list_papers, name="list_papers"),
    path("departments/create/", views.department_create_view, name="department_create"),
    path(
        "departments/<int:department_id>/sections/",
        views.get_sections_by_department,
        name="get_sections_by_department",
    ),
    path("api/skills/", views.get_skills_json, name="get_skills_json"),
    path("skills/", views.skill_list_view, name="skill_list"),
    path("skills/create/", views.skill_create_view, name="skill_create"),
    path("skills/update/<int:pk>/", views.skill_update_view, name="skill_update"),
    path("skills/delete/<int:pk>/", views.skill_delete_view, name="skill_delete"),
    path("paper/<int:paper_id>/", views.paper_detail_view, name="paper_detail"),
    path("paper/<int:paper_id>/edit/", views.paper_edit_view, name="paper_edit"),
    path("paper/take/<int:paper_id>/", views.take_paper, name="take_paper"),
    path(
        "api/paper/<int:paper_id>/toggle-public/",
        views.toggle_paper_public_status,
        name="toggle_paper_public_status",
    ),
    path(
        "paper/<int:paper_id>/partial-update/",
        views.partial_update_view,
        name="partial_update_paper",
    ),
    path("users/", views.user_list, name="user_list"),
    path("users/<int:user_id>/", views.user_detail, name="user_detail"),
    path("users/delete/<int:user_id>/", views.delete_user, name="delete_user"),
    path("profile/<int:pk>/", views.user_profile_view, name="user_profile"),
    path("test-report/<int:registration_id>/", views.testresult, name="test_report"),
    path("regenerate-question/", views.regenerate_question, name="regenerate_question"),
    path(
        "paper/<int:paper_id>/export-participants/",
        views.export_participants_csv,
        name="export_participants_csv",
    ),
    path("submit-test/<int:registration_id>/", views.submit_test, name="submit_test"),
    path(
        "registration/<int:registration_id>/toggle-shortlist/",
        views.toggle_shortlist,
        name="toggle_shortlist",
    ),
    path(
        "invite-candidate/", views.invite_candidate, name="invite_candidate"
    ), 
    path(
    "sections/create/",
    views.create_section_ajax,
    name="create_section_ajax"
),
path('api/skills/search/', views.search_skills_with_suggestions, name='search_skills_suggestions'),



    # Recruitment Drive Management
    path('drives/', views.drive_list_view, name='drive_list'),
    path('drives/create/', views.drive_create_view, name='drive_create'),
    path('drives/<int:drive_id>/', views.drive_detail_view, name='drive_detail'),
    path('drives/<int:drive_id>/edit/', views.drive_edit_view, name='drive_edit'),
    path('drives/<int:drive_id>/delete/', views.drive_delete_view, name='drive_delete'),
    path('drives/<int:drive_id>/toggle-status/', views.toggle_drive_status, name='toggle_drive_status'),
    
    # Candidate Management
    path('drives/<int:drive_id>/candidates/', views.drive_candidates_view, name='drive_candidates'),
    path('drives/<int:drive_id>/candidate/<int:candidate_id>/', views.candidate_detail_view, name='candidate_detail'),
    path('candidates/<int:candidate_id>/update-stage/', views.update_candidate_stage, name='update_candidate_stage'),
    path('candidates/bulk-update/', views.bulk_update_stages, name='bulk_update_stages'),
    
    # Public Application
    path('recruitment/apply/<uuid:drive_uuid>/', views.candidate_apply_view, name='recruitment_apply'),
        path('drives/<int:drive_id>/toggle-link/', views.toggle_drive_link, name='drive_toggle_link'),

    # Analytics & Export
    path('drives/<int:drive_id>/analytics/', views.drive_analytics_view, name='drive_analytics'),
    path('drives/<int:drive_id>/export/', views.export_drive_data, name='export_drive_data'),
path('generator/questions/paper_details/<int:paper_id>/', views.get_paper_details_json, name='paper_details_json'),


      
    #  path('interview/apply/<int:paper_id>/', views.interview_candidate_apply_view, name='interview_candidate_apply'),
path('generator/interview/create/', views.create_interview_round, name='create_interview_round'),


path('interview/apply/<int:paper_id>/', views.interview_candidate_apply_view, name='interview_candidate_apply'),


    
    # View applications for a paper
    path('paper/<int:paper_id>/applications/', 
         views.paper_applications_view, 
         name='paper_applications'),
    
    # View single application detail
    path('application/<int:application_id>/', 
         views.application_detail_view, 
         name='application_detail'),
    
    # Export applications as CSV
    path('paper/<int:paper_id>/applications/export/', 
         views.export_paper_applications_csv, 
         name='export_paper_applications'),
path('submit-application/<int:paper_id>/', views.submit_personal_info_application, name='submit_application'),
path('paper/<int:paper_id>/applications/', views.paper_applications_view, name='paper_applications'),
    # path('recruiter/application/<int:application_id>/', views.application_detail_view, name='application_detail_view'),# Candidate/User Side
    path('my-applied-jobs/', views.applied_jobs_view, name='applied_jobs'),

path(
    "application/<int:application_id>/download-resume/",
    views.download_resume,
    name="download_resume",
),
path('recruiter/application/<int:application_id>/', views.application_detail_view, name='application_detail_view'),
   
   path('applications/kanban/', views.kanban_view, name='kanban_view'),
   path('applications/kanban/update/', views.kanban_update_stage, name='kanban_update_stage'),
    # path('application/detail/<int:application_id>/', views.application_detail_view_candidate, name='candidate_app_detail'),


# New URL for dynamic round creation
    path(
        "api/rounds/create/",
        views.create_custom_round_ajax,
        name="create_custom_round_ajax"
    ),
path('update-candidate-stage/<int:candidate_id>/', views.update_candidate_stage, name='update_candidate_stage'),
    path('application/<int:application_id>/evaluate/<str:round_name>/', 
         views.evaluation_form_view, 
         name='evaluation_form'),

]
