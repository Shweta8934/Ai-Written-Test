# recruitment/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, DetailView
from django.views.generic.edit import FormView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin 
from django.contrib.auth.decorators import login_required 
from django.urls import reverse_lazy, reverse
from django.http import HttpResponseRedirect
from django.db import IntegrityError
from django.contrib import messages
from django.utils.text import slugify 
from .models import JobPost, Candidate, RoundFeedback
from .forms import JobPostForm, RoundFeedbackForm

from user_tests.forms import TestRegistrationForm 
from user_tests.models import TestRegistration 


class JobPostListView(LoginRequiredMixin, ListView):
    model = JobPost
    template_name = 'partials/recruiter/job_list.html'
    context_object_name = 'jobs'
    
class JobPostCreateView(LoginRequiredMixin, CreateView):
    model = JobPost
    form_class = JobPostForm
    template_name = 'partials/recruiter/job_Create.html'    
    success_url = reverse_lazy('job_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        
        # SLUG GENERATION LOGIC:
        base_slug = slugify(form.instance.title)
        unique_slug = base_slug
        num = 1
        
        # Ensure the slug is unique before saving
        while JobPost.objects.filter(public_link_slug=unique_slug).exists():
            unique_slug = f'{base_slug}-{num}'
            num += 1
            
        form.instance.public_link_slug = unique_slug 
        
        # Save the form instance with the generated slug
        response = super().form_valid(form)
        messages.success(self.request, f"Job '{form.instance.title}' created successfully!")
        return response



class JobPostDetailView(LoginRequiredMixin, DetailView):
    model = JobPost
    template_name = 'partials/recruiter/job_list.html'
    context_object_name = 'job'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        job = context['job']
        
        # Pass all jobs for sidebar
        context['jobs'] = JobPost.objects.all()
        
        context['candidate_count'] = job.candidates.count()
        
        # Generate the FULL application link using the slug
        # Ensure 'job_application' URL pattern exists and uses 'slug' parameter
        context['application_link'] = self.request.build_absolute_uri(
            reverse('job_application', kwargs={'slug': job.public_link_slug})
        )
        
        return context


class CandidateListView(LoginRequiredMixin, ListView):
    model = Candidate
    template_name = 'partials/recruiter/candidate_list.html'
    context_object_name = 'candidates'

    def get_queryset(self):
        # Fetch the job post based on the job_pk in the URL
        self.job_post = get_object_or_404(JobPost, pk=self.kwargs['job_pk'])
        # Filter candidates for this job, ordering them by round and score
        return Candidate.objects.filter(job_post=self.job_post).order_by('current_round', '-test_registration__score')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['job'] = self.job_post
        context['round_choices'] = Candidate.ROUND_CHOICES 
        return context

@login_required 
def move_candidate_round(request, pk, round_name):
    """Function to manually or programmatically move a candidate to the next round."""
    candidate = get_object_or_404(Candidate, pk=pk)
    
    # Basic security check against invalid round names
    valid_rounds = [choice[0] for choice in Candidate.ROUND_CHOICES]
    if round_name not in valid_rounds:
        messages.error(request, f"Invalid round name: {round_name}")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('job_list')))

    candidate.current_round = round_name
    candidate.is_hired = (round_name == 'Final Offer') # Set hire status if moving to final offer
    candidate.save()
    
    messages.success(request, f"Candidate {candidate.name} moved to **{round_name}**.")
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('job_list')))


class FeedbackCreateView(LoginRequiredMixin, CreateView):
    model = RoundFeedback
    form_class = RoundFeedbackForm
    template_name = 'recruitment/feedback_form.html'

    def get_success_url(self):
        # Redirect back to the candidate list for the job after successful feedback submission
        return reverse('candidate_list', kwargs={'job_pk': self.object.candidate.job_post.pk})

    def get_initial(self):
        initial = super().get_initial()
        # Pre-fill candidate ID from URL/GET parameter (e.g., ?candidate_id=X)
        initial['candidate_id'] = self.request.GET.get('candidate_id')
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        candidate = get_object_or_404(Candidate, pk=self.request.GET.get('candidate_id'))
        context['candidate'] = candidate
        context['current_round'] = candidate.current_round
        return context

    def form_valid(self, form):
        candidate_id = form.cleaned_data['candidate_id']
        candidate = get_object_or_404(Candidate, pk=candidate_id)

        # Set the required FK fields before saving
        form.instance.candidate = candidate
        form.instance.interviewer = self.request.user
        form.instance.round_name = candidate.current_round # Feedback is for the current round
        
        try:
            response = super().form_valid(form)
            
            # Post-save logic: Update candidate's round based on recommendation (CRITICAL FIX APPLIED HERE)
            recommendation = form.cleaned_data['recommendation']
            round_names = [c[0] for c in Candidate.ROUND_CHOICES]
            current_round_index = round_names.index(candidate.current_round)

            if recommendation == 'Pass':
                
                # If currently in HR Round, move to Final Offer
                if candidate.current_round == 'HR Round':
                    candidate.current_round = 'Final Offer'
                    candidate.is_hired = True
                    messages.success(self.request, f"Feedback submitted. Candidate offered the job!")
                
                # If currently in any round before HR Round, move to the next sequential round
                elif current_round_index < round_names.index('HR Round'):
                    next_round = round_names[current_round_index + 1]
                    candidate.current_round = next_round
                    messages.info(self.request, f"Feedback submitted. Candidate moved to **{next_round}**.")
                
                # Note: If they passed 'Final Offer', do nothing (already hired) or if they passed 'Written Test Passed' it moves to 'GD Round'
                
            elif recommendation == 'Fail':
                candidate.current_round = 'Rejected'
                messages.warning(self.request, f"Feedback submitted. Candidate **Rejected**.")
            
            # Recommendation 'Hold' and any other state does not automatically change the round.
            
            candidate.save()
            return response

        except IntegrityError:
             # This happens if the same user tries to give feedback for the same candidate in the same round again
             messages.error(self.request, f"Feedback already exists for {candidate.name} in the **{candidate.current_round}** round by you.")
             return self.form_invalid(form)



def job_application_view(request, slug):
    """Public view for candidate to register for the written test linked to a job."""
    job_post = get_object_or_404(JobPost, public_link_slug=slug, status='Open')
    
    if not job_post.question_paper:
        messages.error(request, "This job is not currently accepting applications.")
        return redirect('candidate_register') 

    if request.method == 'POST':
        form = TestRegistrationForm(request.POST) # Use the form from user_tests app
        if form.is_valid():
            email = form.cleaned_data['email']
            question_paper = job_post.question_paper
            
            try:
                # 1. Check if registration already exists to avoid duplicate submission
                if TestRegistration.objects.filter(email=email, question_paper=question_paper).exists():
                    messages.warning(request, "You have already registered for this test. Please check your email or resume your test.")
                    # Redirect to a status page or test resume page
                    return redirect('test_status_page') # **Ensure 'test_status_page' is a defined URL**

                # 2. Create/Save TestRegistration
                registration = form.save(commit=False)
                registration.question_paper = question_paper
                registration.save()
                
                # 3. Create Candidate profile for tracking (Default round is 'Applied')
                Candidate.objects.create(
                    test_registration=registration,
                    job_post=job_post,
                    current_round='Applied'
                )
                
                # Redirect to the test start page (assuming your 'user_tests' app handles this)
                messages.success(request, "Registration successful! Starting your written test now.")
                return redirect('test_start_page', paper_id=question_paper.id) 
                
            except IntegrityError:
                # Should be caught by the explicit check above, but serves as a final guard
                messages.warning(request, "An unexpected error occurred. Please try again or contact support.")
                return redirect('login') 

    else:
        form = TestRegistrationForm()

    return render(request, 'partials/recruiter/candidate_list.html', {'job': job_post, 'form': form})



