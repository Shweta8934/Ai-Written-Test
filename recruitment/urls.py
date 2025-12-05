# recruitment/urls.py
from django.urls import path
from . import views

urlpatterns = [
 
    path('jobs/', views.JobPostListView.as_view(), name='job_list'),
    path('jobs/create/', views.JobPostCreateView.as_view(), name='job_create'),
    path('jobs/<int:pk>/', views.JobPostDetailView.as_view(), name='job_detail'),
    path('jobs/<int:job_pk>/candidates/', views.CandidateListView.as_view(), name='candidate_list'),
    path('candidate/<int:pk>/move_to/<str:round_name>/', views.move_candidate_round, name='candidate_move_round'),
    path('candidate/<int:pk>/feedback/submit/', views.FeedbackCreateView.as_view(), name='submit_feedback'),
    path('apply/<slug:slug>/', views.job_application_view, name='job_application'),    
    path('candidate/<int:pk>/feedback/submit/', views.FeedbackCreateView.as_view(), name='submit_feedback'),

]