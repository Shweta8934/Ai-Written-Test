# app/views.py

import json
import re
from typing import Optional, Dict, Any
from openai import OpenAI  
import re
import google.generativeai as genai
from django.contrib.auth import login, logout
from django.views.decorators.http import require_POST
from django.db import transaction
from django.conf import settings
from .forms import QuestionPaperEditForm
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, render, redirect
from .models import QuestionPaper, Question
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .models import QuestionPaper, PaperSection, Question  # Import your models

from .forms import (
    LoginForm,
    UserRegistrationForm,
    UserProfileRegistrationForm,
    DepartmentForm,
    SkillForm,
)
import csv  
from .models import QuestionPaper, PaperSection, Question, Department, Skill
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from .models import (
    TestRegistration,
    UserResponse,
)
from django.views.decorators.csrf import csrf_exempt

from django.contrib import messages


def user_login(request):
    if request.user.is_authenticated:
        return redirect("dashboard") if request.user.is_staff else redirect("home")

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(
                request,
                f"Welcome back, {user.username}! You've successfully logged in. 🎉",
            )

            return redirect("dashboard") if user.is_staff else redirect("home")
    else:
        form = LoginForm()

    return render(request, "login.html", {"form": form, "title": "Login"})


def home(request):
    return render(request, "home.html", {"user": request.user})


def user_logout(request):
    logout(request)
    return redirect("login")


def user_register(request):
    if request.method == "POST":
        user_form = UserRegistrationForm(request.POST)

        if user_form.is_valid():
            user = user_form.save()
            profile_form = UserProfileRegistrationForm(
                request.POST, instance=user.profile
            )
            if profile_form.is_valid():
                profile_form.save()
                return redirect("login")
            else:
                user.delete()

    else:
        user_form = UserRegistrationForm()
        profile_form = UserProfileRegistrationForm()

    if request.method != "POST" or not "user_form" in locals():
        user_form = UserRegistrationForm()
        profile_form = UserProfileRegistrationForm()
    elif "profile_form" not in locals():
        profile_form = UserProfileRegistrationForm(request.POST)

    context = {"user_form": user_form, "profile_form": profile_form}
    return render(request, "registration/register.html", context)


from .models import RecruitmentDrive, CandidateApplication
from django.db.models import Q

from django.db.models import Count, Case, When, IntegerField, F

@login_required
def dashboard(request):
    """
    Main dashboard showing question papers and recruitment drives.
    Uses conditional annotation to count participants based on paper type (written/interview).
    """
    # Get filters from request
    status_filter = request.GET.get('status', 'all')
    experience_filter = request.GET.get('experience', 'all')
    
    # --- 1. Query Question Papers with Conditional Participant Count ---
    
    # Conditional Count Logic:
    # 1. If it's an Interview Round (is_interview_round=True), count linked CandidateApplications.
    # 2. If it's a Written Test (is_interview_round=False), count linked TestRegistrations.
    
    papers_query = QuestionPaper.objects.filter(
        created_by=request.user,
        is_active=True
    ).annotate(
        # Conditional participant_count (Written Test vs. Interview)
        application_or_test_count=Count(
            Case(
                # Case 1: Interview Round -> Count CandidateApplications
                # 🟢 FIX: 'candidateapplication' को 'applications_received' से बदला
                When(is_interview_round=True, then=F('applications_received')), 
                # Case 2: Written Test -> Count TestRegistrations
                When(is_interview_round=False, then=F('testregistration')),
                output_field=IntegerField()
            )
        ),
        participant_count=Count(
            Case(
                # Case 1: Interview Round -> Count CandidateApplications
                # ✅ FIX 1: Using the correct reverse relation name 'applications_received'
                When(is_interview_round=True, then=F('applications_received')), 
                
                # Case 2: Written Test -> Count TestRegistrations
                # ✅ FIX 2: Using the correct reverse relation name 'testregistration'
                When(is_interview_round=False, then=F('testregistration')),
                output_field=IntegerField()
            )
        )
    ).order_by('-created_at')
    
    # Apply status filter
    if status_filter == 'active':
        papers_query = papers_query.filter(is_public_active=True)
    elif status_filter == 'inactive':
        papers_query = papers_query.filter(is_public_active=False)
    
    # Apply experience filter
    if experience_filter != 'all':
        # Assuming you have experience_level field
        papers_query = papers_query.filter(experience_level=experience_filter)
    
    # Pagination for papers
    paginator = Paginator(papers_query, 10)
    page_number = request.GET.get('page')
    papers = paginator.get_page(page_number)
    
    # --- 2. Recruitment Drives Data (Applying FIX for FieldError) ---
    
    from .models import RecruitmentDrive, CandidateApplication
    
    recent_drives = RecruitmentDrive.objects.filter(
        created_by=request.user
    ).annotate(
        # 🟢 FIX: Using the correct reverse relation name (candidateapplication)
        application_count=Count('candidateapplication') 
    ).order_by('-created_at')[:3]
    
    active_drives_count = RecruitmentDrive.objects.filter(
        created_by=request.user,
        drive_status='OPEN'
    ).count()
    
    total_applications = CandidateApplication.objects.filter(
        recruitment_drive__created_by=request.user
    ).count()
    
    in_progress_count = CandidateApplication.objects.filter(
        recruitment_drive__created_by=request.user,
        overall_status='ACTIVE'
    ).count()
    
    hired_count = CandidateApplication.objects.filter(
        recruitment_drive__created_by=request.user,
        overall_status='HIRED'
    ).count()
    
    context = {
        'papers': papers,
        'recent_drives': recent_drives,
        'active_drives_count': active_drives_count,
        'total_applications': total_applications,
        'in_progress_count': in_progress_count,
        'hired_count': hired_count,
        'status_filter': status_filter,
        'experience_filter': experience_filter,
        'title': 'Dashboard'
    }
    
    return render(request, 'dashboard.html', context)


@login_required
def generate_questions(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            job_title = data.get("job_title")
            min_exp = data.get("min_exp")
            max_exp = data.get("max_exp")
            skills_raw = data.get("skills")
            sections_data = data.get("sections", {})
            total_questions = sum(sections_data.values())
            # Department ID ko Department Name mein convert karein
            try:
                department_name = Department.objects.get(id=data.get("departmentId")).name
            except Department.DoesNotExist:
                # Fallback to a default name if not found
                department_name = "N/A"
            seniority = "Junior"
            if int(max_exp) > 5:
                seniority = "Senior"
            elif int(max_exp) > 2:
                seniority = "Mid-Level"


            prompt = f"""
            Act as a seasoned technical assessment creator and principal engineer. Your primary goal is to build a well-balanced and experience-appropriate technical test. The entire response MUST be a single, valid JSON object without any markdown.

            ## Core Specifications
            1.  **Job Role**: {job_title}
            2.  **Experience Level**: {min_exp} to {max_exp} years ({seniority}-level).
            3.  **Core Skills**: {skills_raw}
            4.  **Paper Sections**: {json.dumps(sections_data)}

            ## Guiding Principles: Think Like an Assessor
            You must follow these hierarchical rules precisely.

            1.  **Overall Difficulty**: The complexity of every single question must align with the **{seniority}** level.

            2.  **Question Uniqueness (CRITICAL)**: **ABSOLUTELY NO DUPLICATE QUESTIONS.** Ensure every question generated, across all sections, is unique. If this function is run multiple times, the generated questions must be new and diverse, not a repeat of previously generated content.

            3.  **Situational & Communication Questions**:
                * For non-technical sections like 'Aptitude', provide realistic, job-related scenarios.
                * **For 'Communication' sections, the focus MUST be on evaluating English grammar, syntax, sentence structure, and vocabulary proficiency, NOT general soft skills.** Design questions (MCQ/SA) that test language correctness.

            4.  **⭐ Intelligent Generation for Programming/Coding Sections ⭐**: This is your most important directive. For any section with a title containing 'Programming', 'Coding', or 'Algorithm', you must create an **intelligent mix of question types (`MCQ`, `SA`, `CODE`)** that reflects the candidate's seniority. Do NOT just generate one type of question.

                * **If `{seniority}` is Junior (0-2 yrs)**: The focus is on fundamentals. The **primary quantity and focus MUST be on `CODE` questions**. These `CODE` problems must be simple, foundational problems, equivalent to **LeetCode Easy** level (e.g., array manipulations, string reversals, FizzBuzz, basic data structure implementation). The number of `CODE` questions should be at least **50% of the total** questions in this section, with the remainder being `MCQ` and `SA` on core concepts and predicting output.
                
                * **If `{seniority}` is Mid-Level (3-5 yrs)**: The mix must contain fewer basic MCQs and SAs. The **primary focus and highest quantity of questions MUST be `CODE` problems** of medium complexity (e.g., interacting with data, implementing common algorithms, simple API design). The number of `CODE` questions should **significantly outweigh the sum of `MCQ` and `SA` questions** in this section.
                
                * **If `{seniority}` is Senior (6+ yrs)**: The focus is on depth, design, and complex problem-solving. This section **MUST be overwhelmingly dominated by challenging `CODE` problems**. The number of `CODE` questions must constitute the **vast majority** of the section's total, with any remaining `MCQ` or `SA` questions being highly advanced, focusing on architectural trade-offs or subtle language features, not basics.

            5.  **Answer Formatting**: The format of the question and answer depends strictly on its `type`.
                * For any section with a title containing **'Aptitude' or 'Logical'**: Generate questions purely on **Mathematics, Logical Reasoning, Data Interpretation, and General Problem Solving**, **NEVER** technical skills like React or Python.
                * For **`MCQ` and `SA`** questions: The `answer` must be concise (a word, phrase, or single line of code).
                * For **`CODE`** questions: The `text` must be a full problem description (task, input, expected output). The `answer` must be a complete, multi-line code solution, formatted as a single JSON string with `\\n` for newlines.

            ## Output Structure (Strict)
            - Root JSON object: 'title' (string), 'sections' (array).
            - Section object: 'title' (string), 'questions' (array).
            - Question object: 'text', 'answer', 'type'. `MCQ` types must also have an 'options' array.

            Generate the {seniority}-level assessment now, creating the perfect, balanced mix of questions for each section as instructed.
            """


            # genai.configure(api_key=settings.GEMINI_API_KEY)
            # model = genai.GenerativeModel("gemini-2.5-pro")
            # response = model.generate_content(prompt)

            # json_text = response.text.strip()
            # --- PASTE THIS NEW BLOCK ---
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that generates technical assessments in strictly valid JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )

            json_text = response.choices[0].message.content.strip()
            # ----------------------------
            if json_text.startswith("```json"):
                json_text = json_text[7:]
            if json_text.endswith("```"):
                json_text = json_text[:-3]

            generated_paper = json.loads(json_text)
            # ✅ CRITICAL DEFENSIVE FIX: Ensure question types match client-side expectations
            if generated_paper.get('sections'):
                for section in generated_paper['sections']:
                    if section.get('questions'):
                        for question in section['questions']:
                            # Convert common AI outputs to required format
                            if question.get('type'):
                                q_type = question['type'].upper().strip()
                                if q_type in ('SHORT ANSWER', 'SA', 'SUBJECTIVE'):
                                    question['type'] = 'Short Answer'
                                elif q_type in ('CODE', 'CODING', 'PROGRAMMING'):
                                    question['type'] = 'CODE'
                                elif q_type in ('MCQ', 'MULTIPLE CHOICE'):
                                    question['type'] = 'MCQ'
                                # If none of the above, it remains whatever it was (or will be set below)
                                
                            # Ensure 'options' key exists for non-MCQ types (Python safety, even if redundant for display)
                            if question.get('type') != 'MCQ' and 'options' not in question:
                                question['options'] = []
            
            # --- Continue with the rest of the function ---
            return JsonResponse(generated_paper)
        except json.JSONDecodeError as e:

            return JsonResponse(
                {
                    "error": "Failed to decode the AI's response. The format was invalid."
                },
                status=500,
            )
        except Exception as e:
            print(f"An unexpected error occurred: {str(e)}")
            return JsonResponse(
                {"error": f"An unexpected error occurred: {str(e)}"}, status=500
            )

    departments = Department.objects.all()
    # Note: is_active=True wale papers hi dikhayein
    existing_papers = QuestionPaper.objects.filter(
        created_by=request.user, 
        is_active=True
    ).values(
        'id', 'title', 'duration', 'cutoff_score', 'department_name' 
        # Note: Department ID ki jagah Department Name use kiya (HTML mein 'department' tha)
    ).order_by('-created_at')

    context = {
        "departments": departments,
        "existing_papers": list(existing_papers) # Data ko list mein convert karna
    }
    
    return render(request, "question_generator/generator.html", context)


# @login_required
# @require_POST
# @transaction.atomic
# def save_paper(request):
#     """Saves the generated paper and calculates the total question count."""
#     try:
#         data = json.loads(request.body)

#         total_questions_count = 0
#         for section_data in data.get("sections", []):
#             total_questions_count += len(section_data.get("questions", []))

#         paper = QuestionPaper.objects.create(
#             created_by=request.user,
#             title=data.get("title", "Generated Assessment"),
#             job_title=data.get("job_title"),
#             department_name=data.get("department"),
#             min_exp=data.get("min_exp"),
#             max_exp=data.get("max_exp"),
#             is_active=True,
#             duration=data.get("duration"),
#             is_public_active=False,
#             is_private_link_active=False, 
#              # ✨ NAYA FIELD ADD KAREIN
#             status = models.CharField(
#                 max_length=20,
#                 choices=[
#                     ('draft', 'Draft'),
#                     ('active', 'Active'),
#                     ('inactive', 'Inactive'),
#                     ('archived', 'Archived'),
#                 ],
#                 default='draft',  # ✅ DEFAULT VALUE ZAROORI HAI
#                 help_text="Current status of the question paper"
#             ) ,
#             skills_list=(
#                 ", ".join(data.get("skills", []))
#                 if isinstance(data.get("skills"), list)
#                 else data.get("skills")
#             ),
#             total_questions=total_questions_count,
#         )

#         for section_index, section_data in enumerate(data.get("sections", [])):
#             section = PaperSection.objects.create(
#                 question_paper=paper,
#                 title=section_data.get("title"),
#                 order=section_index,
#             )
#             for q_index, question_data in enumerate(section_data.get("questions", [])):

#                 Question.objects.create(
#                     section=section,
#                     text=question_data.get("text"),
#                     answer=question_data.get("answer"),
#                     options=question_data.get("options"),
#                     order=q_index,
#                     question_type=question_data.get("type", "UN"),
#                 )

#         return JsonResponse(
#             {
#                 "success": True,
#                 "message": "Paper saved successfully!",
#                 "redirect_url": "/dashboard/",
#             }
#         )
#     except Exception as e:
#         print(f"Error saving paper: {e}")
#         return JsonResponse({"success": False, "error": str(e)}, status=400)
from django.views.decorators.http import require_POST
from django.db import transaction
from django.http import JsonResponse
import json
from .models import QuestionPaper, PaperSection, Question




# @require_POST
# @transaction.atomic
# def save_paper(request):
#     try:
#         data = json.loads(request.body)
#         sections_data = data.get("sections", [])
#         total_questions_count = 0
        
#         # --- DEBUGGING PRINT (Aap ise baad mein hata sakte hain) ---
#         print("-------------- DEBUG: DATA RECEIVED ---------------")
#         print(data)
        
#         # Create the main QuestionPaper object
#         paper = QuestionPaper.objects.create(
#             created_by=request.user,
#             title=data.get("title", ""),
#             job_title=data.get("job_title", ""),
#             department_name=data.get("department", ""),
#             min_exp=data.get("min_exp", 0),
#             max_exp=data.get("max_exp", 0),
#             duration=data.get("duration", 0),
#             skills_list=data.get("skills", ""),
#             is_active=True,
#             is_public_active=False,
#             is_private_link_active=False,
#             cutoff_score=data.get("cutoff_score", 20),
#             # ✅ FIX: ADDED MISSING FIELDS FROM THE PAYLOAD
#             job_location=data.get("job_location", ""), # <-- ADD THIS
#             job_type=data.get("job_type", ""),         # <-- ADD THIS
#             positions=data.get("positions", ""),       # <-- ADD THIS
#             rounds=data.get("rounds", ""),             # <-- ADD THIS
#             pay_scale=data.get("pay_scale", ""),       # <-- ADD THIS
#             end_date=data.get("end_date", None),       # <-- ADD THIS (Keep None for DateField if blank allowed)
#         )
        
#         # ✅ FIXED: Create sections and questions with proper weightage handling
#         for section_index, section_data in enumerate(sections_data):
#             # Extract and validate section weightage
#             section_weightage = 0.0
#             try:
#                 weightage_raw = section_data.get("weightage", 0.0)
#                 section_weightage = float(weightage_raw)
#             except (ValueError, TypeError) as e:
#                 print(f"Weightage conversion error for section {section_index}: {e}")
#                 section_weightage = 0.0
            
#             # ✅ FIX: weightage parameter ko add kiya gaya hai
#             section = PaperSection.objects.create(
#                 question_paper=paper,
#                 title=section_data.get("title", f"Section {section_index}"),
#                 order=section_index,
#                 weightage=section_weightage  # ✅ YEH LINE MISSING THI
#             )
            
#             questions = section_data.get("questions", [])
#             total_questions_count += len(questions)
            
#             # Create questions for this section
#             for q_index, question_data in enumerate(questions):
#                 Question.objects.create(
#                     section=section,
#                     text=question_data.get("text", ""),
#                     answer=question_data.get("answer", ""),
#                     options=question_data.get("options", None),
#                     order=q_index,
#                     question_type=question_data.get("type", "MCQ")
#                 )

#         # Update total_questions count
#         paper.total_questions = total_questions_count
#         paper.save(update_fields=["total_questions"])
        
#         return JsonResponse({
#             "success": True,
#             "message": "Paper saved successfully!",
#             "redirect_url": "/dashboard"
#         })
        
#     except Exception as e:
#         # Server-side error logging
#         print(f"Error saving paper: {str(e)}") 
        
#         return JsonResponse({
#             "success": False,
#             "error": f"Failed to save paper: {str(e)}"
#         }, status=400)


# app/views.py

@require_POST
@transaction.atomic
def save_paper(request):
    try:
        data = json.loads(request.body)
        sections_data = data.get("sections", [])
        total_questions_count = 0
        
        # --- 1. DETERMINE PAPER TYPE ---
        # अगर sections_data मौजूद है और उसमें questions हैं, तो यह Written Assessment है।
        # इंटरव्यू राउंड के लिए, client-side से sections array खाली आना चाहिए (या total_questions 0 होना चाहिए)।
        
        # हम is_interview_round को data payload से निकालने की कोशिश कर सकते हैं, 
        # लेकिन सुरक्षित तरीका total_questions_count को चेक करना है।
        
        for section_data in sections_data:
            total_questions_count += len(section_data.get("questions", []))

        # तय करें कि क्या यह इंटरव्यू राउंड है (total_questions 0 के बराबर हैं)
        is_interview = (total_questions_count == 0)
        
        # इंटरव्यू राउंड के लिए duration और cutoff को 0/N/A पर सेट करें
        duration = 0 if is_interview else data.get("duration", 0)
        cutoff_score = 0 if is_interview else data.get("cutoff_score", 20)
        title = data.get("title", "Interview Round") if is_interview else data.get("title", "Generated Assessment")
        
        # Create the main QuestionPaper object
        paper = QuestionPaper.objects.create(
            created_by=request.user,
            title=title,
            job_title=data.get("job_title", ""),
            department_name=data.get("department", ""),
            min_exp=data.get("min_exp", 0),
            max_exp=data.get("max_exp", 0),
            
            # ⭐ CRITICAL: DURATION AND CUTOFF ARE CONDITIONAL ⭐
            duration=duration, 
            cutoff_score=cutoff_score, 
            
            skills_list=data.get("skills", ""),
            is_active=True,
            is_public_active=False,
            is_private_link_active=False,
            
            # ⭐ CRITICAL: SET THE NEW FIELD HERE ⭐
            is_interview_round=is_interview, 
            
            job_location=data.get("job_location", ""), 
            job_type=data.get("job_type", ""),
            positions=data.get("positions", ""),
            rounds=data.get("rounds", ""),
            pay_scale=data.get("pay_scale", ""),
            end_date=data.get("end_date", None),
            
            # Temporarily set total_questions to 0/correct count
            total_questions=total_questions_count, 
        )
        
        # --- 2. SAVE SECTIONS AND QUESTIONS (Only for Written Assessment) ---
        if not is_interview:
            for section_index, section_data in enumerate(sections_data):
                section_weightage = 0.0
                try:
                    weightage_raw = section_data.get("weightage", 0.0)
                    section_weightage = float(weightage_raw)
                except (ValueError, TypeError) as e:
                    print(f"Weightage conversion error for section {section_index}: {e}")
                    section_weightage = 0.0
                
                section = PaperSection.objects.create(
                    question_paper=paper,
                    title=section_data.get("title", f"Section {section_index}"),
                    order=section_index,
                    weightage=section_weightage
                )
                
                questions = section_data.get("questions", [])
                
                for q_index, question_data in enumerate(questions):
                    Question.objects.create(
                        section=section,
                        text=question_data.get("text", ""),
                        answer=question_data.get("answer", ""),
                        options=question_data.get("options", None),
                        order=q_index,
                        question_type=question_data.get("type", "MCQ")
                    )

        # Total questions are already correct (0 for interview, count for written), so save is redundant but safe.
        # paper.total_questions = total_questions_count
        # paper.save(update_fields=["total_questions"])
        
        message = "Interview Round saved successfully!" if is_interview else "Paper saved successfully!"
        
        return JsonResponse({
            "success": True,
            "message": message,
            "redirect_url": "/dashboard"
        })
        
    except Exception as e:
        print(f"Error saving paper: {str(e)}") 
        return JsonResponse({
            "success": False,
            "error": f"Failed to save paper: {str(e)}"
        }, status=400)

@login_required
def list_papers(request):
    papers = QuestionPaper.objects.filter(created_by=request.user).order_by(
        "-created_at"
    )
    return render(request, "question_generator/list_papers.html", {"papers": papers})




def take_paper(request, paper_id):
    """
    Handles the request for a public or invited user to take a question paper.
    """
    paper = get_object_or_404(QuestionPaper, pk=paper_id)

    if not paper.is_public_active:
        return render(request, "link_deactivated.html", status=403)

    invited_email = request.GET.get("email")

    redirect_url = reverse("test:user_register_link", kwargs={"link_id": str(paper.id)})

    if invited_email:
        return redirect(f"{redirect_url}?email={invited_email}")

    return redirect(redirect_url)


from django.urls import reverse  
from urllib.parse import urlencode  

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import QuestionPaper, TestRegistration


from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import QuestionPaper, TestRegistration


from .models import UserResponse

@login_required
def paper_detail_view(request, paper_id):
    """
    Displays the details of a single question paper.
    FIXED: Conditionally fetches TestRegistration or CandidateApplication based on paper type.
    """
    paper = get_object_or_404(QuestionPaper, pk=paper_id, created_by=request.user)
    status_filter = request.GET.get("status", "all")
    shortlist_filter = request.GET.get("shortlist_status", "all")

    skills = [skill.strip() for skill in paper.skills_list.split(",") if skill.strip()]

    # --- CRITICAL FIX: Conditionally fetch data ---
    is_interview = paper.is_interview_round

    if is_interview:
        # For Interview Rounds: Fetch CandidateApplications
        # Note: 'applications_received' is the correct related_name on QuestionPaper model.
        all_participants_query = paper.applications_received.all().order_by("-applied_at")
        
        # Interview Applications ke liye koi scoring ya completion status nahi hota.
        # Hum is data ko TestRegistration format mein map karenge taki template render ho sake.
        all_participants = []
        for app in all_participants_query:
            # Map CandidateApplication to a mock structure for the template
            mock_participant = {
                'id': app.id,
                'email': app.email,
                'phone_number': app.phone_number,
                'is_completed': True, # Interview submission is final, so treat as completed
                'is_shortlisted': app.overall_status == 'ACTIVE', # Use overall_status for mock shortlist
                'score': None, # Score is irrelevant for interview rounds
                'status': app.get_current_stage_display().lower(),
                'full_name': app.full_name,
            }
            all_participants.append(mock_participant)
        
        
    else:
        # For Written Tests: Fetch TestRegistrations (Your existing logic)
        paper_sections = list(paper.paper_sections.all().prefetch_related('questions'))
        all_participants = list(
            TestRegistration.objects.filter(question_paper=paper).order_by("-start_time")
        )
        
        
        
        for p in all_participants:
            if p.is_completed:
                # --- START: EXISTING WEIGHTED SCORING LOGIC ---
                user_responses = UserResponse.objects.filter(registration=p).select_related('question')
                total_weighted_score = 0.0
                
                for section in paper_sections:
                    section_total = section.questions.count()
                    section_correct = 0
                    
                    for response in user_responses:
                        question = response.question
                        if question and question.section_id == section.id:
                            # Scoring logic (MCQ vs AI-evaluated) is here (re-using test_result logic)
                            user_answer = response.user_answer.strip()
                            is_correct = False
                            
                            if not user_answer:
                                is_correct = False
                            elif question.question_type == "MCQ":
                                cleaned_answer = re.sub(r"<[^>]+>", "", question.answer).strip()
                                is_correct = user_answer.lower() == cleaned_answer.lower()
                            else:
                                qtype = question.question_type.upper()
                                # Simplified evaluator_type mapping
                                evaluator_type = "coding" if qtype in ("CODE", "CODING") else "short" 

                                # You need to ensure 'evaluate_answer_with_ai' is accessible. 
                                # Since it's defined later in your file, it should be fine, but 
                                # if you move it, you'll need a proper import.
                                is_correct, _ = evaluate_answer_with_ai(
                                    question_text=question.text,
                                    user_answer=user_answer,
                                    model_answer=question.answer.strip(),
                                    question_type=evaluator_type,
                                )

                            if is_correct:
                                section_correct += 1
                                
                    if section_total > 0:
                        section_percentage = (section_correct / section_total) * 100
                        weighted_score = (section_percentage * section.weightage) / 100 if section.weightage else 0
                        total_weighted_score += weighted_score

                final_percentage = round(total_weighted_score, 2)
                p.score = final_percentage
                cutoff = p.question_paper.cutoff_score

                if cutoff is not None and final_percentage >= cutoff:
                    p.status = "pass"
                else:
                    p.status = "fail"
            else:
                p.status = "pending"
                p.score = 0
            # --- END: EXISTING WEIGHTED SCORING LOGIC ---
            
    # Apply filters to the processed data
    filtered_participants = []
    
    # 📝 Interview Round ke liye 'status' field CandidateApplication.current_stage se map kiya gaya hai
    #  Written Test ke liye, 'status' calculated field hai.
    for p in all_participants:
        # Convert dictionary keys to attribute access if needed for existing template code
        participant = p if is_interview else p
        
        status_match = (status_filter == "all") or (
            (is_interview and participant['status'] == status_filter) or 
            (not is_interview and participant.status == status_filter)
        )
        
        shortlist_match = (shortlist_filter == "all") or (
            (is_interview and participant['is_shortlisted']) if shortlist_filter == "shortlisted" else 
            (is_interview and not participant['is_shortlisted']) if shortlist_filter == "not_shortlisted" else 
            (not is_interview and participant.is_shortlisted) if shortlist_filter == "shortlisted" else 
            (not is_interview and not participant.is_shortlisted)
        )
        
        if status_match and shortlist_match:
            filtered_participants.append(participant)


    context = {
        "paper": paper,
        "is_interview": is_interview, # Pass this flag to the template for conditional display
        "skills": skills,
        "participants": filtered_participants,
        "title": f"Details for {paper.title}",
        "selected_status": status_filter,
        "selected_shortlist_status": shortlist_filter,
        "candidate_stages": CandidateApplication.CandidateStage.choices # For Interview filters
    }
    return render(request, "question_generator/paper_detail.html", context)


# @login_required
# def paper_detail_view(request, paper_id):
#     """
#     Displays the details of a single question paper with WEIGHTED SCORING logic.
#     """
#     paper = get_object_or_404(QuestionPaper, pk=paper_id, created_by=request.user)
#     status_filter = request.GET.get("status", "all")
#     shortlist_filter = request.GET.get("shortlist_status", "all")

#     skills = [skill.strip() for skill in paper.skills_list.split(",") if skill.strip()]

#     # Fetch all sections once to avoid repetitive DB calls inside the loop
#     paper_sections = list(paper.paper_sections.all().prefetch_related('questions'))

#     all_participants = list(
#         TestRegistration.objects.filter(question_paper=paper).order_by("-start_time")
#     )

#     # ▼▼▼ UPDATED LOGIC: WEIGHTED SCORING (Same as test_report) ▼▼▼
#     for p in all_participants:
#         if p.is_completed:
#             user_responses = UserResponse.objects.filter(registration=p).select_related('question')
            
#             total_weighted_score = 0.0  # Initialize weighted score
            
#             # Iterate through each section to calculate weighted score
#             for section in paper_sections:
#                 section_questions = section.questions.all()
#                 section_total = len(section_questions)
#                 section_correct = 0
                
#                 # Calculate correct answers for this specific section
#                 for response in user_responses:
#                     question = response.question
#                     # Check if response belongs to current section
#                     if question and question.section_id == section.id:
#                         user_answer = response.user_answer.strip()
#                         is_correct = False

#                         if not user_answer:
#                             is_correct = False
#                         elif question.question_type == "MCQ":
#                             cleaned_answer = re.sub(r"<[^>]+>", "", question.answer).strip()
#                             is_correct = user_answer.lower() == cleaned_answer.lower()
#                         else:
#                             # AI Evaluation Logic reusing existing function
#                             qtype = question.question_type.upper()
#                             if qtype in ("CODE", "CODING"):
#                                 evaluator_type = "coding"
#                             elif qtype in ("SA", "SHORT", "SUBJECTIVE"):
#                                 evaluator_type = "short"
#                             elif qtype in ("TF", "TRUE_FALSE", "BOOLEAN"):
#                                 evaluator_type = "true_false"
#                             else:
#                                 evaluator_type = "short"

#                             is_correct, _ = evaluate_answer_with_ai(
#                                 question_text=question.text,
#                                 user_answer=user_answer,
#                                 model_answer=question.answer.strip(),
#                                 question_type=evaluator_type,
#                             )

#                         if is_correct:
#                             section_correct += 1
                
#                 # Apply Section Weightage Logic
#                 if section_total > 0:
#                     section_percentage = (section_correct / section_total) * 100
#                     # Weightage apply karein
#                     weighted_score = (section_percentage * section.weightage) / 100 if section.weightage else 0
#                     total_weighted_score += weighted_score

#             # Final calculation
#             final_percentage = round(total_weighted_score, 2)
#             p.score = final_percentage  # Update the score object for display
            
#             cutoff = p.question_paper.cutoff_score

#             if cutoff is not None:
#                 if final_percentage >= cutoff:
#                     p.status = "pass"
#                 else:
#                     p.status = "fail"
#             else:
#                 p.status = "pass"
#         else:
#             p.status = "pending"
#             p.score = 0
#     # ▲▲▲ END OF UPDATED LOGIC ▲▲▲

#     if status_filter != "all":
#         filtered_participants = [
#             p for p in all_participants if p.status == status_filter
#         ]
#     else:
#         filtered_participants = all_participants

#     if shortlist_filter == "shortlisted":
#         final_participants = [p for p in filtered_participants if p.is_shortlisted]
#     elif shortlist_filter == "not_shortlisted":
#         final_participants = [p for p in filtered_participants if not p.is_shortlisted]
#     else:
#         final_participants = filtered_participants

#     context = {
#         "paper": paper,
#         "skills": skills,
#         "participants": final_participants,
#         "title": f"Details for {paper.title}",
#         "selected_status": status_filter,
#         "selected_shortlist_status": shortlist_filter,
#     }
#     return render(request, "question_generator/paper_detail.html", context)



@login_required
@transaction.atomic
def paper_edit_view(request, paper_id):
    """
    Handles editing of a question paper's metadata and its questions.
    NOW ALSO SAVES MCQ OPTIONS!
    """
    paper = get_object_or_404(QuestionPaper, pk=paper_id, created_by=request.user)

    if request.method == "POST":
        form = QuestionPaperEditForm(request.POST, instance=paper)

        if form.is_valid():
            updated_paper = form.save()

            total_questions_count = 0

            for section in paper.paper_sections.all():
                # ▼▼▼ YEH NAYA LOGIC ADD KAREIN ▼▼▼
                # Section ka weightage save karein
                weightage_key = f"section-weightage-{section.id}"
                if weightage_key in request.POST:
                    try:
                        # Value ko float mein convert karein, default 0.0
                        new_weightage = float(request.POST[weightage_key] or 0.0)
                        section.weightage = new_weightage
                        # Section ko database mein save karein
                        section.save(update_fields=["weightage"]) # <--- यह सेव कर रहा है
                    except (ValueError, TypeError):
                        # Agar koi galat value (jaise text) daalta hai, toh use ignore karein
                        pass
                # ▲▲▲ NAYA LOGIC KHATAM ▲▲▲
                for question in section.questions.all():
                    question_text_name = f"question-text-{question.id}"
                    question_answer_name = f"question-answer-{question.id}"

                    if question_text_name in request.POST:
                        new_text = request.POST[question_text_name].strip()
                        if new_text:  
                            question.text = new_text

                    if question_answer_name in request.POST:
                        new_answer = request.POST[question_answer_name].strip()
                        if new_answer:  
                            question.answer = new_answer
                        if question.question_type == "MCQ":
                            options = []
                            for opt_num in range(1, 11):  
                                option_key = f"option-{question.id}-{opt_num}"
                                if option_key in request.POST:
                                    option_value = request.POST[option_key].strip()
                                    if option_value:
                                        options.append(option_value)
                            if options:
                                question.options = options

                        question.save()
                   
                    total_questions_count += 1

            updated_paper.total_questions = total_questions_count
            updated_paper.save(update_fields=["total_questions"])

            messages.success(
                request,
                f"✅ Paper '{updated_paper.title}' successfully updated with {total_questions_count} questions!",
            )
            return redirect("paper_detail", paper_id=paper.id)

        else:
            messages.error(
                request,
                "❌ There were errors in your submission. Please check the form.",
            )

    else:
        form = QuestionPaperEditForm(instance=paper)

    context = {"form": form, "paper": paper, "title": f"Edit {paper.title}"}

    return render(request, "question_generator/paper_edit.html", context)


import logging

logger = logging.getLogger(__name__)




#     context = {"form": form}
#     return render(request, "partials/department/department_create.html", context)
# app/views.py

@login_required
def department_create_view(request):
    if request.method == "POST":
        form = DepartmentForm(request.POST)
        if form.is_valid():
            try:
                # ✨ CHANGE 1: Pehle Department instance banayein par abhi database main pura commit na karein
                department = form.save(commit=False)
                # Department ko save karein taaki usse ek ID mil jaye
                department.save()

                # ✨ CHANGE 2: Ab explicitly Many-to-Many relations (sections) ko save karein
                form.save_m2m()

                messages.success(request, "Department created successfully!")
                return redirect("dashboard")
            except Exception as e:
                logger.error(f"Error creating department: {e}", exc_info=True)
                messages.error(request, f"Error: {e}")
                return redirect("department_create")
        else:
            messages.warning(request, "Please correct the errors below.")
    else:
        form = DepartmentForm()

    context = {"form": form}
    return render(request, "partials/department/department_create.html", context)

@login_required
def get_skills_json(request):
    """Returns a JSON list of all active skills."""
    skills = Skill.objects.filter(is_active=True).values("id", "name")
    return JsonResponse({"skills": list(skills)})


@login_required
def skill_list_view(request):
    """Page load karne aur saare active skills dikhane ke liye."""
    skills = Skill.objects.filter(is_active=True)
    context = {
        "skills": skills,
    }
    return render(request, "partials/skills/skill_list.html", context)


@login_required
@require_POST
def skill_create_view(request):
    """AJAX request se naya skill banane ke liye."""
    try:
        data = json.loads(request.body)
        form = SkillForm(data)
        if form.is_valid():
            skill = form.save()
            return JsonResponse(
                {
                    "status": "success",
                    "skill": {
                        "id": skill.id,
                        "name": skill.name,
                        "is_active": skill.is_active,
                    },
                },
                status=201,
            )
        else:
            return JsonResponse({"status": "error", "errors": form.errors}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)


@login_required
@require_POST
def skill_update_view(request, pk):
    """(Naya View) AJAX request se skill ko edit/update karne ke liye."""
    try:
        skill = get_object_or_404(Skill, pk=pk)
        data = json.loads(request.body)
        form = SkillForm(data, instance=skill)
        if form.is_valid():
            updated_skill = form.save()
            return JsonResponse(
                {
                    "status": "success",
                    "skill": {"id": updated_skill.id, "name": updated_skill.name},
                },
            )
        else:
            return JsonResponse({"status": "error", "errors": form.errors}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)


@login_required
@require_POST
def skill_delete_view(request, pk):
    """AJAX request se skill delete karne ke liye."""
    skill = get_object_or_404(Skill, pk=pk)
    skill.delete()
    return JsonResponse({"status": "success", "message": "Skill deleted successfully."})


User = get_user_model()


def user_list(request):
    users = TestRegistration.objects.all().order_by("id")
    return render(request, "partials/users/user_list.html", {"users": users})


def user_detail(request, user_id):
    registration = get_object_or_404(TestRegistration, pk=user_id)

    context = {
        "registration": registration,
    }
    return render(request, "partials/users/user_details.html", context)


@login_required
def delete_user(request, user_id):
    user_to_delete = get_object_or_404(User, pk=user_id)

    if user_to_delete == request.user:
        messages.error(request, "You cannot delete your own account.")
        return redirect("user_list")

    if user_to_delete.is_superuser:
        messages.error(request, "Superusers cannot be deleted.")
        return redirect("user_list")

    if request.method == "POST":
        user_to_delete.delete()
        messages.success(
            request, f"User '{user_to_delete.username}' has been deleted successfully."
        )
        return redirect("user_list")

    context = {"user_to_delete": user_to_delete}
    return render(request, "partials/users/confirm_user_delete.html", context)


@login_required
def user_profile_view(request, pk):
    profile_user = get_object_or_404(User, pk=pk)

    context = {"profile_user": profile_user}

    return render(request, "partials/users/profile.html", context)


def get_sections_by_department(request, department_id):
    try:
        department = Department.objects.get(pk=department_id)
        sections = department.sections.all().values_list("name", flat=True)
        return JsonResponse({"sections": list(sections)})
    except Department.DoesNotExist:
        return JsonResponse({"sections": []}, status=404)


@login_required
@require_POST
def toggle_paper_public_status(request, paper_id):
    """
    Toggles the public accessibility (is_public_active field) of a QuestionPaper.
    This is called by the JavaScript fetch() from the share modal.
    """
    try:
        paper = QuestionPaper.objects.get(pk=paper_id, created_by=request.user)

        paper.is_public_active = not paper.is_public_active
        paper.save()

        return JsonResponse(
            {
                "status": "success",
                "message": "Paper status updated successfully.",
                "is_public_active": paper.is_public_active,
            }
        )

    except QuestionPaper.DoesNotExist:
        return JsonResponse(
            {
                "status": "error",
                "message": "Paper not found or you do not have permission to modify it.",
            },
            status=404,
        )


# def test_result(request, registration_id):
#     """
#     Displays test results with clear indication of unattempted questions.
#     """
#     registration = get_object_or_404(TestRegistration, pk=registration_id)
#     user_responses = UserResponse.objects.filter(
#         registration=registration
#     ).select_related("question")

#     paper = registration.question_paper
#     total_questions = paper.total_questions
#     cutoff_score = paper.cutoff_score

#     score = 0
#     results_data = []
#     unattempted_count = 0  # ✅ NEW: Track unattempted questions

#     for response in user_responses:
#         question = response.question
#         user_answer = response.user_answer.strip()
#         is_correct = False
#         attempt_status = "incorrect"  # ✅ NEW: Default status

#         # ✅ Check if question was attempted
#         if not user_answer:
#             attempt_status = "unattempted"
#             unattempted_count += 1
#         else:
#             # Question attempt kiya gaya hai, ab evaluate karo
#             if question.question_type == "MCQ":
#                 model_answer = question.answer.strip()
#                 is_correct = user_answer.lower() == model_answer.lower()
#             else:
#                 # Map internal question type to evaluator type
#                 qtype = question.question_type.upper()
#                 if qtype in ("CODE", "CODING"):
#                     evaluator_type = "coding"
#                 elif qtype in ("SA", "SHORT", "SUBJECTIVE"):
#                     evaluator_type = "short"
#                 elif qtype in ("TF", "TRUE_FALSE", "BOOLEAN"):
#                     evaluator_type = "true_false"
#                 else:
#                     evaluator_type = "short"

#                 # evaluate_answer_with_ai returns (is_correct, details)
#                 is_correct, _ = evaluate_answer_with_ai(
#                     question_text=question.text,
#                     user_answer=user_answer,
#                     model_answer=question.answer.strip(),
#                     question_type=evaluator_type,
#                 )

#             # Set status based on correctness
#             if is_correct:
#                 score += 1
#                 attempt_status = "correct"
#             else:
#                 attempt_status = "incorrect"

#         results_data.append(
#             {
#                 "question_text": response.question.text,
#                 "user_answer": (
#                     response.user_answer if user_answer else "Not Attempted"
#                 ),  # ✅ NEW
#                 "correct_answer": response.question.answer,
#                 "is_correct": is_correct,
#                 "attempt_status": attempt_status,  # ✅ NEW: Pass status to template
#             }
#         )

#     incorrect_answers = total_questions - score - unattempted_count  # ✅ UPDATED
#     percentage = round((score / total_questions) * 100) if total_questions > 0 else 0

#     status = "Pass" if percentage >= cutoff_score else "Fail"

#     context = {
#         "registration": registration,
#         "results": results_data,
#         "score": score,
#         "total_questions": total_questions,
#         "incorrect_answers": incorrect_answers,
#         "unattempted_count": unattempted_count,  # ✅ NEW
#         "percentage": percentage,
#         "title": f"Test Report for {registration.email}",
#         "status": status,
#         "cutoff_score": cutoff_score,
#     }

#     return render(request, "partials/users/test_report.html", context)
# app/views.py

def testresult(request, registration_id):
    """Displays test results with section-wise weightage breakdown."""
    registration = get_object_or_404(TestRegistration, pk=registration_id)
    user_responses = UserResponse.objects.filter(
        registration=registration
    ).select_related('question')
    
    paper = registration.question_paper
    total_questions = paper.total_questions
    cutoff_score = paper.cutoff_score
    
    # Overall scoring
    score = 0
    results_data = []
    
    # Section-wise scoring
    section_scores = []
    total_weighted_score = 0  # <-- YEH LINE ADD KAREIN
    
    for section in paper.paper_sections.all():
        section_questions = section.questions.all()
        section_total = len(section_questions)
        section_correct = 0
        
        for response in user_responses:
            question = response.question
            if question.section == section:
                user_answer = response.user_answer.strip()
                is_correct = False
                
                if not user_answer:
                    is_correct = False
                elif question.question_type == "MCQ":
                    model_answer = question.answer.strip()
                    is_correct = user_answer.lower() == model_answer.lower()
                else:
                    qtype = question.question_type.upper()
                    if qtype in ["CODE", "CODING"]:
                        evaluator_type = "coding"
                    elif qtype in ["SA", "SHORT", "SUBJECTIVE"]:
                        evaluator_type = "short"
                    elif qtype in ["TF", "TRUEFALSE", "BOOLEAN"]:
                        evaluator_type = "truefalse"
                    else:
                        evaluator_type = "short"
                    
                    is_correct, _ = evaluate_answer_with_ai(
                        question_text=question.text,
                        user_answer=user_answer,
                        model_answer=question.answer.strip(),
                        question_type=evaluator_type,
                    )
                
                if is_correct:
                    section_correct += 1
                    score += 1 # Yeh raw score hai (e.g., 15/20)
        
        # Calculate section percentage and weighted score
        section_percentage = round((section_correct / section_total) * 100, 2) if section_total > 0 else 0
        weighted_score = round((section_percentage * section.weightage) / 100, 2) if section.weightage else 0
        
        total_weighted_score += weighted_score  # <-- YEH LINE ADD KAREIN (Total mein add karein)
        
        section_scores.append({
            'title': section.title,
            'weightage': section.weightage,        # (e.g., 20)
            'correct': section_correct,
            'total': section_total,
            'percentage': section_percentage,      # (e.g., 80.0)
            'weighted_score': weighted_score,      # (e.g., 16.0)
        })
    
    # ... (Build results_data for individual questions... yeh code same rahega) ...
    for response in user_responses:
        question = response.question
        user_answer = response.user_answer.strip()
        is_correct = False
        
        if not user_answer:
            is_correct = False
        elif question.question_type == "MCQ":
            model_answer = question.answer.strip()
            is_correct = user_answer.lower() == model_answer.lower()
        else:
            qtype = question.question_type.upper()
            if qtype in ["CODE", "CODING"]:
                evaluator_type = "coding"
            elif qtype in ["SA", "SHORT", "SUBJECTIVE"]:
                evaluator_type = "short"
            elif qtype in ["TF", "TRUEFALSE", "BOOLEAN"]:
                evaluator_type = "truefalse"
            else:
                evaluator_type = "short"
            
            is_correct, _ = evaluate_answer_with_ai(
                question_text=question.text,
                user_answer=user_answer,
                model_answer=question.answer.strip(),
                question_type=evaluator_type,
            )
        
        results_data.append({
            'question_text': question.text,
            'user_answer': user_answer if user_answer else "(No answer)",
            'correct_answer': question.answer,
            'is_correct': is_correct,
        })
        
    incorrect_answers = total_questions - score
    
    # --- AB HUM 'percentage' KO BHI WEIGHTED SCORE SE REPLACE KAR DENGE ---
    percentage = round(total_weighted_score, 2) # <-- YEH LINE BADLEIN
    status = "Pass" if percentage >= cutoff_score else "Fail"
    
    context = {
        'registration': registration,
        'results': results_data,
        'score': score,
        'total_questions': total_questions,
        'incorrect_answers': incorrect_answers,
        'percentage': percentage, # Yeh ab weighted score hai
        'title': f"Test Report for {registration.email}",
        'status': status,
        'cutoff_score': cutoff_score,
        'section_scores': section_scores,
        'total_weighted_score': total_weighted_score, # <-- YEH LINE ADD KAREIN
    }
    
    return render(request, 'partials/users/test_report.html', context)

@csrf_exempt
def partial_update_view(request, paper_id):
    if request.method == "POST":
        try:
            paper = QuestionPaper.objects.get(pk=paper_id)
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse(
                    {"status": "error", "message": "Invalid JSON payload."}, status=400
                )

            if "job_title" in data:
                paper.job_title = data["job_title"] or paper.job_title
            if "duration" in data:
                paper.duration = data["duration"] or paper.duration
            if "skills_list" in data:
                skills_list = data["skills_list"]
                if isinstance(skills_list, list):
                    paper.skills = ",".join(skills_list)
                else:
                    return JsonResponse(
                        {"status": "error", "message": "skills_list must be a list."},
                        status=400,
                    )

            paper.save()

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Paper updated successfully!",
                    "updated_data": {
                        "job_title": paper.job_title,
                        "duration": paper.duration,
                        "skills_list": paper.skills.split(",") if paper.skills else [],
                    },
                }
            )

        except QuestionPaper.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Paper not found."}, status=404
            )
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse(
        {"status": "error", "message": "Invalid request method."}, status=405
    )


@require_POST
def regenerate_question(request):
    try:
        data = json.loads(request.body)
        job_title = data.get("job_title")
        skills = data.get("skills")
        section_title = data.get("section_title")
        question_type = data.get("question_type")
        question_text = data.get("question_text")

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-pro")

        prompt = f"""
        As an expert technical recruiter, generate ONE new and different interview question based on the following context.
        The previous question was: "{question_text}". Do not repeat this question.

        CONTEXT:
        - Job Title: {job_title}
        - Required Skills: {skills}
        - Test Section: {section_title}
        - Question Type: {question_type}

        Generate a completely new question that assesses a similar concept but is not identical.
        
        Provide the output in a strict JSON format with no extra text or markdown formatting.
        The JSON object must have these keys: "text" (string), "type" (string, e.g., "MCQ"), "options" (an array of 4 strings for MCQ, or null for other types), and "answer" (string).
        
        Example for MCQ:
        {{
            "text": "What is the primary purpose of a virtual environment in Python?",
            "type": "MCQ",
            "options": ["To run Python code faster", "To isolate project dependencies", "To share code easily", "To write Python code"],
            "answer": "To isolate project dependencies"
        }}
        """

        response = model.generate_content(prompt)
        cleaned_response = (
            response.text.strip().replace("```json", "").replace("```", "")
        )
        new_question = json.loads(cleaned_response)

        return JsonResponse(new_question)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# @login_required
# @require_POST
# def deactivate_paper(request, paper_id):
#     """
#     Soft deletes a question paper by setting its is_active flag to False.
#     """
#     try:

#         paper = get_object_or_404(QuestionPaper, pk=paper_id, created_by=request.user)

#         paper.is_active = False
#         paper.save()

#         return JsonResponse(
#             {
#                 "status": "success",
#                 "message": f'Paper "{paper.title}" has been deactivated successfully.',
#             }
#         )

#     except QuestionPaper.DoesNotExist:
#         return JsonResponse(
#             {
#                 "status": "error",
#                 "message": "Paper not found or you do not have permission to perform this action.",
#             },
#             status=404,
#         )
#     except Exception as e:
#         return JsonResponse({"status": "error", "message": str(e)}, status=500)
# app/views.py

# ... (baaki saare imports)
from django.utils import timezone  # Yeh add karein
import datetime  # Yeh add karein
# ... (baaki saare imports)


@login_required
@require_POST
def deactivate_paper(request, paper_id):
    """
    Soft deletes a paper.
    NEW: Checks for genuinely active test takers (within their time limit).
    """
    try:
        paper = get_object_or_404(QuestionPaper, pk=paper_id, created_by=request.user)

        # --- YEH HAI BEHTAR CHECK ---
        
        # 1. Paper ka duration (minutes mein) lein
        duration_minutes = paper.duration
        
        active_takers_exist = False  # Pehle se False maan lein

        if duration_minutes and duration_minutes > 0:
            # 2. "Cutoff" time calculate karein.
            # Agar test 60 min ka hai, toh hum sirf unhe dhoondhenge
            # jinhone pichle 60 minute ke andar test start kiya tha.
            # Jo 60 min se pehle start kiye the, unka time waise hi khatam ho chuka hai.
            cutoff_time = timezone.now() - datetime.timedelta(minutes=duration_minutes)

            # 3. Query: Kya koi aisa user hai jo...
            #    - test complete nahi kiya hai (is_completed=False)
            #    - AND test pichle [duration] minutes ke andar start kiya tha? 
            #      (matlab unka time abhi chal raha hai)
            active_takers_exist = TestRegistration.objects.filter(
                question_paper=paper,
                is_completed=False,
                start_time__gt=cutoff_time  # Check: start_time cutoff ke BAAD ka hai
            ).exists()

        else:
            # 4. Agar paper ka duration 0 ya None hai, toh purana (safe) logic use karein
            #    (jo check karta hai ki kya koi bhi incomplete test hai)
            active_takers_exist = TestRegistration.objects.filter(
                question_paper=paper,
                is_completed=False,
                start_time__isnull=False
            ).exists()

        # --- CHECK KHATAM ---

        if active_takers_exist:
            # Agar active takers hain, toh error message ke saath 400 status return karein
            return JsonResponse(
                {
                    "status": "error",
                    "message": (
                        f'Cannot deactivate paper "{paper.title}". '
                        "One or more users are currently within their active test session."
                    ),
                },
                status=400,
            )

        # Agar koi active taker nahi hai, toh paper ko deactivate karein
        paper.is_active = False
        paper.save()

        return JsonResponse(
            {
                "status": "success",
                "message": f'Paper "{paper.title}" has been deactivated successfully.',
            }
        )

    except QuestionPaper.DoesNotExist:
        return JsonResponse(
            {
                "status": "error",
                "message": "Paper not found or you do not have permission to perform this action.",
            },
            status=404,
        )
        
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

from django.contrib.auth import get_user_model


@login_required
def export_participants_csv(request, paper_id):
    """
    Exports a detailed list of participants to a CSV file.
    """
    paper = get_object_or_404(QuestionPaper, pk=paper_id, created_by=request.user)
    User = get_user_model()  # Get the active User model

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="participants_{paper.job_title.replace(" ", "_")}_{paper.id}.csv"'
    )

    writer = csv.writer(response)

    # Updated header row
    writer.writerow(["Full Name", "Email", "Phone Number", "Username", "Test Status"])

    participants = TestRegistration.objects.filter(question_paper=paper).order_by(
        "-start_time"
    )

    for participant in participants:
        status = "Completed" if participant.is_completed else "Pending"

        # --- FIX STARTS HERE ---
        # Instead of checking for 'participant.user', we try to find a user
        # by matching the email address.
        try:
            user = User.objects.get(email__iexact=participant.email)
            # If a user is found, get their details
            full_name = user.get_full_name() or user.username
            username = user.username
        except User.DoesNotExist:
            # If no user is found with that email, they are a guest
            full_name = "Guest User"
            username = "N/A"
        # --- FIX ENDS HERE ---

        # Write the data to the CSV row
        writer.writerow(
            [full_name, participant.email, participant.phone_number, username, status]
        )

    return response


from django.utils import timezone


from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import TestRegistration


@login_required
@require_POST
def toggle_shortlist(request, registration_id):
    """
    TestRegistration ke liye is_shortlisted status ko toggle karta hai aur
    change ko database mein SAVE karta hai.
    """
    registration = get_object_or_404(TestRegistration, id=registration_id)

    # Boolean value ko ulta karein (True se False, False se True)
    registration.is_shortlisted = not registration.is_shortlisted

    # ▼▼▼ YEH LINE SABSE ZARURI HAI ▼▼▼
    # Change ko database mein save karein.
    registration.save(update_fields=["is_shortlisted"])
    # ▲▲▲ YAHI FIX HAI ▲▲▲

    # Naye status ke saath success response return karein
    return JsonResponse(
        {"status": "success", "is_shortlisted": registration.is_shortlisted}
    )


import json
import re
from typing import Tuple, Dict, Any
import google.generativeai as genai
from django.conf import settings


# def evaluate_answer_with_ai(
#     question_text: str,
#     user_answer: str,
#     model_answer: str,
#     question_type: str = "short",
# ) -> Tuple[bool, Dict[str, Any]]:
#     """
#     Uses Gemini AI to evaluate if a user's answer is conceptually correct.

#     Args:
#         question_text: The question being asked
#         user_answer: User's submitted answer
#         model_answer: Correct/reference answer
#         question_type: Type of question - "mcq", "short", "coding", "true_false"

#     Returns:
#         Tuple of (is_correct: bool, details: dict with confidence and reason)
#     """
#     # Empty answer check
#     if not user_answer or not user_answer.strip():
#         return False, {
#             "is_correct": False,
#             "confidence": 100,
#             "reason": "Answer is empty",
#         }

#     # Normalize inputs
#     user_answer = user_answer.strip()
#     model_answer = model_answer.strip()

#     try:
#         # Quick checks for specific question types before AI call
#         if question_type.lower() == "mcq":
#             return _evaluate_mcq(user_answer, model_answer)

#         elif question_type.lower() in ["true_false", "boolean"]:
#             return _evaluate_boolean(user_answer, model_answer)

#         # AI evaluation for short answer and coding
#         genai.configure(api_key=settings.GEMINI_API_KEY)
#         model = genai.GenerativeModel("gemini-2.0-flash-exp")

#         # Different prompts for different question types
#         if question_type.lower() == "coding":
#             prompt = _get_coding_prompt(question_text, user_answer, model_answer)
#         else:
#             prompt = _get_short_answer_prompt(question_text, user_answer, model_answer)

#         response = model.generate_content(prompt)
#         cleaned_text = response.text.strip()

#         # Remove markdown code blocks if present
#         if cleaned_text.startswith("```json"):
#             cleaned_text = cleaned_text[7:]
#         elif cleaned_text.startswith("```"):
#             cleaned_text = cleaned_text[3:]
#         if cleaned_text.endswith("```"):
#             cleaned_text = cleaned_text[:-3]
#         cleaned_text = cleaned_text.strip()

#         result = json.loads(cleaned_text)

#         is_correct = result.get("is_correct", False)
#         return is_correct, result

#     except json.JSONDecodeError as e:

#         return _fallback_evaluation(user_answer, model_answer, question_type)

#     except Exception as e:
#         print(f"AI Evaluation Error: {e}")
#         return _fallback_evaluation(user_answer, model_answer, question_type)

import json
import re
from typing import Tuple, Dict, Any
from django.conf import settings
from openai import OpenAI  # Import OpenAI instead of google.generativeai

# OpenAI Client initialize karein
client = OpenAI(api_key=settings.OPENAI_API_KEY)

def evaluate_answer_with_ai(
    question_text: str,
    user_answer: str,
    model_answer: str,
    question_type: str = "short",
) -> Tuple[bool, Dict[str, Any]]:
    """
    Uses OpenAI GPT-4o-mini to evaluate if a user's answer is conceptually correct.
    """
    # Empty answer check
    if not user_answer or not user_answer.strip():
        return False, {
            "is_correct": False,
            "confidence": 100,
            "reason": "Answer is empty",
        }

    # Normalize inputs
    user_answer = user_answer.strip()
    model_answer = model_answer.strip()

    try:
        # Quick checks for specific question types before AI call
        if question_type.lower() == "mcq":
            return _evaluate_mcq(user_answer, model_answer)

        elif question_type.lower() in ["true_false", "boolean"]:
            return _evaluate_boolean(user_answer, model_answer)

        # --- AI Evaluation Section Changed Here ---

        # Different prompts for different question types
        if question_type.lower() == "coding":
            prompt = _get_coding_prompt(question_text, user_answer, model_answer)
            system_instruction = "You are an expert programming instructor evaluating code. Output ONLY JSON."
        else:
            prompt = _get_short_answer_prompt(question_text, user_answer, model_answer)
            system_instruction = "You are an expert technical evaluator. Output ONLY JSON."

        # OpenAI API Call
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Lower temperature for more consistent evaluations
            max_tokens=500,
            response_format={"type": "json_object"}  # Forces valid JSON output
        )

        # Extract content
        cleaned_text = response.choices[0].message.content.strip()
        result = json.loads(cleaned_text)
# fallback heuristic
        q_tokens = set(re.findall(r"\w+", (question_text or "").lower()))
        a_tokens = set(re.findall(r"\w+", ua))
        is_correct = result.get("is_correct", False)
        return is_correct, result

    except json.JSONDecodeError:
        print("AI Evaluation Error: Invalid JSON received from OpenAI")
        return _fallback_evaluation(user_answer, model_answer, question_type)

    except Exception as e:
        print(f"AI Evaluation Error: {e}")
        return _fallback_evaluation(user_answer, model_answer, question_type)

def _get_short_answer_prompt(
    question_text: str, user_answer: str, model_answer: str
) -> str:
    """Generate prompt for short answer evaluation"""
    return f"""You are an expert technical evaluator. Evaluate if the user's answer demonstrates understanding of the concept.

**Question:**
{question_text}

**Reference Answer:**
{model_answer}

**User's Answer:**
{user_answer}

**Evaluation Criteria:**
1. Check if the user's answer conveys the CORE CONCEPT correctly
2. Accept answers that are at least 50% conceptually correct
3. Ignore minor grammar mistakes, typos, spelling errors, or extra/missing articles
4. Accept synonyms, paraphrases, and alternative explanations if conceptually correct
5. Accept answers in different languages (Hindi/English/Hinglish) if meaning is correct
6. Focus on understanding, not exact word matching
7. Accept partial answers if they cover the main points
8. Be lenient with formatting, structure, and presentation
9. Accept additional correct information beyond the reference answer
10. Ignore irrelevant extra words if core concept is present

**Examples of Acceptable Variations:**
- Technical terms with synonyms: "function" = "method", "array" = "list", "variable" = "identifier"
- Word order changes that preserve meaning
- Additional explanations, examples, or context
- Simpler or more complex language that captures the concept
- Missing articles (a, an, the), conjunctions, or prepositions
- Common abbreviations: "func", "var", "obj", "arr"
- Different sentence structures expressing same idea
- Casual/conversational tone vs formal tone

**Scoring Guide:**
- is_correct: true if answer demonstrates understanding (50%+ concept match)
- is_correct: false if answer is fundamentally wrong or irrelevant
- confidence: 90-100% for excellent answers
- confidence: 70-89% for good answers with minor issues
- confidence: 50-69% for acceptable answers covering basics
- confidence: below 50% for incorrect/incomplete answers

Respond with ONLY a valid JSON object (no markdown, no extra text):
{{
    "is_correct": true/false,
    "confidence": 0-100,
    "reason": "brief explanation in one line"
}}"""


# def _get_coding_prompt(question_text: str, user_code: str, model_code: str) -> str:
#     """
#     Generate prompt for coding evaluation with cross-language flexibility criteria.
#     (MODIFIED FOR LANGUAGE FLEXIBILITY - FOR DIRECT PASTE)
#     """
#     return f"""You are an expert programming instructor. Evaluate if the user's code correctly solves the problem.

# **Question:**
# {question_text}

# **Reference Solution (Use for context, but do not require exact matching):**
# ```
# {model_code}
# ```

# **User's Code:**
# ```
# {user_code}
# ```

# **Evaluation Criteria:**
# 1. **CRITICAL: The user's code MUST solve the specific problem described in the Question.**

# 2. **⭐ Cross-Language Tolerance (FLEXIBLE LOGIC) ⭐:**
#     * **If the QUESTION text DOES NOT explicitly name a programming language** (e.g., "Write a function...", "Solve this problem..."), **then ACCEPT the solution, even if the language of the User's Code differs from the Reference Solution, provided the core logic is sound.** The goal is to check technical skill, not language specific adherence, unless requested.
#     * If the **QUESTION text EXPLICITLY specifies a language** (e.g., "Write a JavaScript function...", "Implement this in Python"), then **code in a different language should result in is_correct: false**, regardless of the logic.

# 3. The core logic must be sound, even if the implementation style differs.
# 4. Accept different approaches: loops vs. comprehensions, recursion vs. iteration.
# 5. Accept different but correct algorithms.
# 6. Ignore minor syntax variations: spacing, indentation, bracket styles.
# 7. Accept more efficient or optimized solutions.

# **What to REJECT (This must result in is_correct: false):**
# - **Code that solves a COMPLETELY DIFFERENT PROBLEM than the one asked.**
# - Logic errors that produce incorrect output.
# - Missing critical functionality.
# - **Code in a different language when the question explicitly mandated a specific one.**

# **Scoring Guide:**
# - is_correct: true if code would work and solve the problem (50%+ functionality)
# - is_correct: false if code has fundamental logic errors or solves the wrong problem
# - confidence: 90-100% for perfect or near-perfect solutions
# - confidence: 70-89% for working solutions with minor issues

# Respond with ONLY valid JSON (no markdown, no extra text):
# {{
#     "is_correct": true/false,
#     "confidence": 0-100,
#     "reason": "brief explanation"
# }}"""
def _get_coding_prompt(question_text: str, user_code: str, model_code: str) -> str:
    """
    Generate a highly flexible prompt that forces AI to ignore language differences
    and boilerplate code unless specifically required by the question.
    """
    return f"""You are an expert multi-language code evaluator. Your ONLY job is to check if the user's logic solves the problem, regardless of the language used.

**Question:**
{question_text}

**User's Code (EVALUATE THIS LOGIC):**
```
{user_code}

**Question:**
{question_text}

**User's Code (Evaluate THIS based on its own language's syntax/logic):**

**Reference Solution (FOR CONTEXT ONLY - IGNORE LANGUAGE USED HERE):**


**CRITICAL EVALUATION RULES (MUST FOLLOW):**
1. **🚫 IGNORE LANGUAGE RESTRICTIONS (UNLESS EXPLICIT):**
   - If the question does NOT explicitly say "Write in JavaScript" (or another specific language), you **MUST ACCEPT** solutions in **Java, Python, C++, C, SQL, or JavaScript**.
   - The user's language DOES NOT need to match the Reference Solution's language.

2. **🏗️ IGNORE BOILERPLATE & STRUCTURE:**
   - In Java/C++, users often need full classes (`public class Main { ... }`) to run code. **DO NOT mark this wrong** if the question only asked for a "function".
   - Focus ONLY on the core logic inside the function/method that solves the problem.

3. **✅ LOGIC IS KING:**
   - Does the code actually solve the problem?
   - If it runs and produces the correct output (like "madam" -> true), it is **CORRECT**.
   - Ignore minor syntax errors (like missing semicolons) if the logic is sound.

**SCORING:**
- `is_correct: true` -> Logic is correct in ANY standard standard programming language.
- `is_correct: false` -> Logic is wrong, OR question EXPLICITLY forbade this language.

Output strictly valid JSON:
{{
    "is_correct": true/false,
    "confidence": 0-100,
    "reason": "One sentence feedback focusing ONLY on logic."
}}"""

def _evaluate_mcq(user_answer: str, model_answer: str) -> Tuple[bool, Dict]:
    """Evaluate MCQ answers with flexibility for different formats"""

    # Normalize both answers
    user_clean = re.sub(r"[^\w\s]", "", user_answer.lower()).strip()
    model_clean = re.sub(r"[^\w\s]", "", model_answer.lower()).strip()

    # Direct match
    if user_clean == model_clean:
        return True, {"is_correct": True, "confidence": 100, "reason": "Exact match"}

    # Extract option letters (A, B, C, D)
    option_patterns = [
        r"^([a-d])\)?\.?\s*",  # A, A), A.
        r"option\s*([a-d])",  # Option A
        r"^([a-d])\s*[-:]\s*",  # A - something, A: something
        r"\(([a-d])\)",  # (A)
        r"answer\s*:?\s*([a-d])",  # Answer: A
    ]

    user_option = None
    model_option = None

    for pattern in option_patterns:
        if not user_option:
            user_match = re.search(pattern, user_answer.lower())
            if user_match:
                user_option = user_match.group(1)

        if not model_option:
            model_match = re.search(pattern, model_answer.lower())
            if model_match:
                model_option = model_match.group(1)

    # Compare extracted options
    if user_option and model_option:
        if user_option == model_option:
            return True, {
                "is_correct": True,
                "confidence": 95,
                "reason": f"Correct option: {user_option.upper()}",
            }
        else:
            return False, {
                "is_correct": False,
                "confidence": 100,
                "reason": f"Wrong option: {user_option.upper()} (correct: {model_option.upper()})",
            }

    # Full text comparison (if user wrote full option text)
    if len(user_clean) > 3 and len(model_clean) > 3:
        if user_clean in model_clean or model_clean in user_clean:
            return True, {
                "is_correct": True,
                "confidence": 90,
                "reason": "Answer matches option text",
            }

        # Word overlap check
        user_words = set(user_clean.split())
        model_words = set(model_clean.split())
        if len(model_words) > 0:
            overlap = len(user_words & model_words) / len(model_words)
            if overlap > 0.7:
                return True, {
                    "is_correct": True,
                    "confidence": int(overlap * 100),
                    "reason": f"High text similarity: {overlap:.0%}",
                }

    return False, {"is_correct": False, "confidence": 100, "reason": "Incorrect option"}


def _evaluate_boolean(user_answer: str, model_answer: str) -> Tuple[bool, Dict]:
    """Evaluate True/False questions with support for multiple formats"""

    # Define variants for True
    true_variants = [
        "true",
        "t",
        "yes",
        "y",
        "1",
        "correct",
        "right",
        "sahi",
        "han",
        "haan",
        "sach",
        "theek",
        "✓",
        "tick",
        "check",
    ]

    # Define variants for False
    false_variants = [
        "false",
        "f",
        "no",
        "n",
        "0",
        "incorrect",
        "wrong",
        "galat",
        "nahi",
        "nai",
        "jhoot",
        "ghalat",
        "✗",
        "cross",
        "x",
    ]

    user_clean = user_answer.lower().strip()
    model_clean = model_answer.lower().strip()

    # Check what user answered
    user_is_true = any(variant in user_clean for variant in true_variants)
    user_is_false = any(variant in user_clean for variant in false_variants)

    # Check correct answer
    model_is_true = any(variant in model_clean for variant in true_variants)
    model_is_false = any(variant in model_clean for variant in false_variants)

    # If both detected in user answer, take first occurrence
    if user_is_true and user_is_false:
        first_true = min(
            (user_clean.find(v) for v in true_variants if v in user_clean), default=999
        )
        first_false = min(
            (user_clean.find(v) for v in false_variants if v in user_clean), default=999
        )
        user_is_true = first_true < first_false
        user_is_false = not user_is_true

    # Compare answers
    if model_is_true and user_is_true:
        return True, {"is_correct": True, "confidence": 100, "reason": "Correct: True"}
    elif model_is_false and user_is_false:
        return True, {"is_correct": True, "confidence": 100, "reason": "Correct: False"}
    elif not model_is_false and user_is_false:
        return False, {
            "is_correct": False,
            "confidence": 100,
            "reason": "Incorrect: answered False (correct: True)",
        }
    elif not model_is_true and user_is_true:
        return False, {
            "is_correct": False,
            "confidence": 100,
            "reason": "Incorrect: answered True (correct: False)",
        }

    # If we can't determine, return False
    return False, {
        "is_correct": False,
        "confidence": 50,
        "reason": "Could not determine boolean value from answer",
    }


def _fallback_evaluation(
    user_answer: str, model_answer: str, question_type: str
) -> Tuple[bool, Dict]:
    """Fallback evaluation when AI fails"""

    user_clean = user_answer.lower().strip()
    model_clean = model_answer.lower().strip()

    # Exact match
    if user_clean == model_clean:
        return True, {
            "is_correct": True,
            "confidence": 100,
            "reason": "Exact match (fallback mode)",
        }

    # Substring match for longer answers
    if len(user_clean) > 10 and (
        user_clean in model_clean or model_clean in user_clean
    ):
        return True, {
            "is_correct": True,
            "confidence": 85,
            "reason": "Substring match (fallback mode)",
        }

    # Word overlap for short answers
    user_words = set(re.findall(r"\w+", user_clean))
    model_words = set(re.findall(r"\w+", model_clean))

    # Remove common stop words
    stop_words = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "and",
        "or",
        "but",
    }
    user_words -= stop_words
    model_words -= stop_words

    if len(model_words) > 0:
        overlap = len(user_words & model_words) / len(model_words)

        # For coding, be more strict
        threshold = 0.4 if question_type.lower() == "coding" else 0.6

        if overlap >= threshold:
            return True, {
                "is_correct": True,
                "confidence": int(overlap * 100),
                "reason": f"Word overlap: {overlap:.0%} (fallback mode)",
            }

    # For very short answers, check if user answer is substring
    if len(model_words) <= 3 and len(user_words & model_words) >= 1:
        return True, {
            "is_correct": True,
            "confidence": 70,
            "reason": "Key term match (fallback mode)",
        }

    return False, {
        "is_correct": False,
        "confidence": 60,
        "reason": "No sufficient match (fallback mode)",
    }


# Backward compatible wrapper (returns only boolean like your original)
def evaluate_answer_simple(
    question_text: str, user_answer: str, model_answer: str
) -> bool:
    """
    Simple version that returns only True/False (backward compatible)
    """
    is_correct, _ = evaluate_answer_with_ai(
        question_text, user_answer, model_answer, "short"
    )
    return is_correct


@require_POST
def submit_test(request, registration_id):
    """
    Evaluates test submission, distinguishing between incorrect and unattempted answers.
    """
    registration = get_object_or_404(TestRegistration, pk=registration_id)

    if registration.is_completed:
        return redirect("test_result", registration_id=registration.id)

    user_responses = UserResponse.objects.filter(
        registration=registration
    ).select_related("question")

    total_questions = registration.question_paper.total_questions
    correct_answers_count = 0

    for response in user_responses:
        question = response.question
        user_answer = response.user_answer.strip()
        is_correct = False

        if user_answer:
            if question.question_type == "MCQ":
                model_answer = question.answer.strip()
                is_correct = user_answer.lower() == model_answer.lower()
            else:
                # Map internal question type to evaluator type
                qtype = question.question_type.upper()
                if qtype in ("CODE", "CODING"):
                    evaluator_type = "coding"
                elif qtype in ("SA", "SHORT", "SUBJECTIVE"):
                    evaluator_type = "short"
                elif qtype in ("TF", "TRUE_FALSE", "BOOLEAN"):
                    evaluator_type = "true_false"
                else:
                    evaluator_type = "short"

                # evaluate_answer_with_ai returns (is_correct, details)
                is_correct, _ = evaluate_answer_with_ai(
                    question_text=question.text,
                    user_answer=user_answer,
                    model_answer=question.answer.strip(),
                    question_type=evaluator_type,
                )

            if is_correct:
                correct_answers_count += 1

    # Calculate score
    percentage_score = 0
    if total_questions > 0:
        percentage_score = round((correct_answers_count / total_questions) * 100, 2)

    # Save results
    registration.is_completed = True
    registration.end_time = timezone.now()
    registration.score = percentage_score
    registration.save(update_fields=["is_completed", "end_time", "score"])

    return redirect("test_result", registration_id=registration.id)


from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import views as auth_views
from django.shortcuts import render

User = get_user_model()

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import views as auth_views
from django.shortcuts import render
from django.urls import reverse  #

User = get_user_model()


def password_reset_request(request):
    """
    Custom view jo email ko DB mein check karta hai aur agar milta hai,
    to Django ke default reset process ko aage badhata hai.
    """
    template_name = "registration/password_reset_form.html"

    if request.method == "POST":
        email = request.POST.get("email", "").strip()

        try:
            User.objects.get(email__iexact=email, is_active=True)

        except User.DoesNotExist:
            messages.error(
                request,
                "The email address you entered is not associated with any active account. Please check it and try again. 🧐",
            )
            return render(request, template_name, {})

      
        return auth_views.PasswordResetView.as_view(template_name=template_name)(
            request
        )

    return auth_views.PasswordResetView.as_view(template_name=template_name)(request)


from django.core.mail import send_mail  
from django.template.loader import render_to_string 
from django.utils.html import strip_tags  
from .forms import (
   SectionForm,
    SkillForm,
    InviteCandidateForm,  
)


from django.urls import reverse
from urllib.parse import urlencode  


@login_required
@require_POST
def invite_candidate(request):
    """
    Handles the AJAX request to invite a candidate via email.
    FIXED: Now adds email parameter to the link.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"status": "error", "message": "Invalid JSON data."}, status=400
        )

    form = InviteCandidateForm(data)

    if form.is_valid():
        candidate_email = form.cleaned_data["email"]
        paper_id = form.cleaned_data["paper_id"]

        try:
            paper = QuestionPaper.objects.get(pk=paper_id, created_by=request.user)
        except QuestionPaper.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Paper not found or unauthorized."},
                status=404,
            )

        if not paper.is_public_active:
            paper.is_public_active = True
            paper.save(update_fields=["is_public_active"])
            messages.info(
                request, f"Public link for '{paper.title}' was automatically activated."
            )

        registration_url = reverse(
            "test:user_register_link", kwargs={"link_id": str(paper.id)}
        )

        query_string = urlencode({"email": candidate_email})
        test_link = request.build_absolute_uri(f"{registration_url}?{query_string}")

        context = {
            "paper_title": paper.title,
            "job_title": paper.job_title,
            "recruiter_name": request.user.get_full_name() or request.user.username,
            "test_link": test_link,  
            "duration": paper.duration,
            "total_questions": paper.total_questions,
            "skills_list": paper.skills_list.split(","),
        }

       
        html_message = render_to_string("emails/candidate_invite.html", context)
        plain_message = strip_tags(html_message)

        try:
            send_mail(
                subject=f"Invitation to Take Assessment: {paper.title} for {paper.job_title}",
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[candidate_email],
                html_message=html_message,
                fail_silently=False,
            )
            return JsonResponse(
                {
                    "status": "success",
                    "message": f"Invitation sent successfully to {candidate_email}!",
                    "is_public_active": paper.is_public_active,
                },
                status=200,
            )

        except Exception as e:
            logger.error(f"Error sending email to {candidate_email}: {e}")
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Email sending failed. Please check server logs.",
                },
                status=500,
            )
    else:
        return JsonResponse(
            {
                "status": "error",
                "message": "Form validation failed.",
                "errors": form.errors,
            },
            status=400,
        )



@login_required
@require_POST
def create_section_ajax(request):
    """
    AJAX endpoint to create a new section.
    """
    try:
        data = json.loads(request.body)
        form = SectionForm(data)
        
        if form.is_valid():
            section = form.save()
            return JsonResponse({
                "status": "success",
                "section": {
                    "id": section.id,
                    "name": section.name
                }
            }, status=201)
        else:
            return JsonResponse({
                "status": "error",
                "errors": form.errors
            }, status=400)
    except json.JSONDecodeError:
        return JsonResponse({
            "status": "error",
            "message": "Invalid JSON"
        }, status=400)

# @login_required
# def search_skills_with_suggestions(request):
#     '''User type करे तो AI suggest करे'''
#     query = request.GET.get('q', '').strip().lower()
    
#     if not query or len(query) < 2:
#         return JsonResponse({'skills': [], 'suggestions': []})
    
#     try:
#         # DB में खोजो
#         db_skills = Skill.objects.filter(
#             name__icontains=query,
#             is_active=True
#         ).values_list('name', flat=True)[:5]
        
#         db_list = list(db_skills)
        
#         if len(db_list) >= 3:
#             return JsonResponse({'skills': db_list, 'suggestions': []})
        
#         genai.configure(api_key=settings.GEMINI_API_KEY)
#         model = genai.GenerativeModel('gemini-2.5-pro')
        
#         prompt = f'Technical recruiting expert: User typed "{query}". Suggest 7-10 related tech skills. Only skill names, one per line.'
        
#         response = model.generate_content(prompt)
#         ai_suggestions = [
#             s.strip() for s in response.text.split('\n')
#             if s.strip() and len(s.strip()) > 2
#         ][:6]
        
#         return JsonResponse({
#             'skills': db_list,
#             'suggestions': ai_suggestions
#         })
    
#     except Exception as e:
#         return JsonResponse({'skills': [], 'suggestions': []}, status=500)


from openai import OpenAI

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth.decorators import login_required
from .models import Skill  
import os

     

import openai
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from .models import Skill 
from thefuzz import process, fuzz

@login_required
@require_http_methods(["GET"])
def search_skills_with_suggestions(request):
    query = request.GET.get('q', '').strip().lower()
    ai_provider = request.GET.get('provider', 'chatgpt').lower()
    
    if not query:
        return JsonResponse({'skills': [], 'suggestions': []})
    
    try:
       
        
        all_active_skills = list(Skill.objects.filter(is_active=True).values_list('name', flat=True))
       
        fuzzy_results = process.extract(query, all_active_skills, limit=50, scorer=fuzz.WRatio)
        
        # Sirf wahi rakhein jinka match score > 60 ho (adjust as needed)
        # fuzzy_results format: [('SkillName', score), ...]
        db_list = [res[0] for res in fuzzy_results if res[1] >= 65]

        # --- 2. AI LOGIC ---
        # CHANGE: 'len(query) < 3' ko 'len(query) < 2' kar diya taaki "fi" par bhi AI call ho sake
        # agar DB results kam hain (less than 10 kar diya taaki AI zyada active rahe choti queries par)
        if len(query) < 1 or len(db_list) >= 50:
             return JsonResponse({'skills': db_list, 'suggestions': []})
        
        if ai_provider == 'gemini':
             ai_suggestions = [] # Gemini implement hone par yahan add karein
        else:
            # Agar DB results bahut kam hain, tabhi AI call karein
            ai_suggestions = get_chatgpt_suggestions(query, db_list)
        
        ai_suggestions = ai_suggestions[:15]
        
        return JsonResponse({
            'skills': db_list,
            'suggestions': ai_suggestions,
            'provider': 'chatgpt'
        })
    
    except Exception as e:
        print(f"Search Error: {e}")
        return JsonResponse({'skills': [], 'suggestions': [], 'error': str(e)})

def get_chatgpt_suggestions(query, db_list):
    """Get 15 skill suggestions using OpenAI API"""
    try:
        # Check if key exists
        if not settings.OPENAI_API_KEY: return []

        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        excluded = ', '.join([f'"{s}"' for s in db_list]) if db_list else 'none'
        
        # CHANGE HERE: Prompt mein 15 maange hain
        system_prompt = "You are a technical recruiting expert. Output only a comma-separated list of 15 related short technical skill names. No explanations."
        user_prompt = f'User typed: "{query}". Exclude these DB results: {excluded}. Suggest 15 related technical skills.'

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.4,
            max_tokens=200 # Tokens badha diye kyunki 15 skills zyada space lengi
        )
        
        content = response.choices[0].message.content
        if content:
            raw_suggestions = content.replace('\n', ',').split(',')
            ai_suggestions = []
            for s in raw_suggestions:
                clean_s = s.strip().strip('.- •')
                if clean_s and len(clean_s) > 1 and clean_s.lower() not in [x.lower() for x in db_list]:
                    ai_suggestions.append(clean_s)
            return ai_suggestions
            
        return []

    except Exception as e:
        print(f"OpenAI Error: {e}")
        return []



# ============ RECRUITMENT DRIVE VIEWS ============

from .models import RecruitmentDrive, CandidateApplication
from .forms import RecruitmentDriveForm, CandidateApplicationForm, CandidateStageUpdateForm, BulkStageUpdateForm

# Drive Management Views

@login_required
def drive_list_view(request):
    """List all drives created by the user"""
    status_filter = request.GET.get('status', 'all')
    
    drives_query = RecruitmentDrive.objects.filter(created_by=request.user)
    
    if status_filter != 'all':
        drives_query = drives_query.filter(drive_status=status_filter.upper())
    
    drives = drives_query.annotate(
        application_count=Count('applications')
    ).order_by('-created_at')
    
    paginator = Paginator(drives, 10)
    page_number = request.GET.get('page')
    drives_page = paginator.get_page(page_number)
    
    context = {
        'drives': drives_page,
        'selected_status': status_filter,
        'title': 'Recruitment Drives'
    }
    return render(request, 'recruitment/drive_list.html', context)


# @login_required
# @transaction.atomic
# def drive_create_view(request):
#     """Create a new recruitment drive"""
#     if request.method == 'POST':
#         form = RecruitmentDriveForm(request.POST)
#         if form.is_valid():
#             drive = form.save(commit=False)
#             drive.created_by = request.user
#             drive.save()
#             form.save_m2m()  # Save many-to-many relationships
            
#             messages.success(request, f"Drive '{drive.title}' created successfully!")
#             return redirect('drive_detail', drive_id=drive.id)
#     else:
#         form = RecruitmentDriveForm()
    
#     context = {'form': form, 'title': 'Create Recruitment Drive'}
#     return render(request, 'recruitment/drive_form.html', context)
# @login_required
# @transaction.atomic
# def drive_create_view(request):
#     """Create a new recruitment drive"""
#     if request.method == 'POST':
#         form = RecruitmentDriveForm(request.POST)
#         if form.is_valid():
#             drive = form.save(commit=False)
#             drive.created_by = request.user
#             drive.drive_status = 'OPEN'  # ✅ Set to OPEN instead of DRAFT
#             drive.save()
#             form.save_m2m()  # Save many-to-many relationships
            
#             messages.success(request, f"Drive '{drive.title}' created successfully!")
#             return redirect('drive_detail', drive_id=drive.id)
#     else:
#         form = RecruitmentDriveForm()
    
#     context = {'form': form, 'title': 'Create Recruitment Drive'}
#     return render(request, 'recruitment/drive_form.html', context)
@login_required
@transaction.atomic
def drive_create_view(request):
    """Create a new recruitment drive"""
    if request.method == 'POST':
        form = RecruitmentDriveForm(request.POST)
        if form.is_valid():
            drive = form.save(commit=False)
            drive.created_by = request.user
            drive.drive_status = 'OPEN'  # ✅ Set to OPEN by default
            drive.is_public_link_active = True  # ✅ Activate public link
            drive.save()
            form.save_m2m()  # Save many-to-many relationships
            
            messages.success(request, f"Drive '{drive.title}' created successfully! Public link is active.")
            return redirect('drive_detail', drive_id=drive.id)
    else:
        form = RecruitmentDriveForm()
    
    context = {'form': form, 'title': 'Create Recruitment Drive'}
    return render(request, 'recruitment/drive_form.html', context)


@login_required
def drive_detail_view(request, drive_id):
    """Show detailed view of a recruitment drive"""
    drive = get_object_or_404(RecruitmentDrive, pk=drive_id, created_by=request.user)
    
    # Get stage-wise breakdown
    stage_counts = drive.get_stage_wise_count()
    
    # Get recent candidates
    recent_candidates = drive.applications.all()[:10]
    
    # Get test papers linked to this drive
    test_papers = drive.test_papers.all()
    
    context = {
        'drive': drive,
        'stage_counts': stage_counts,
        'recent_candidates': recent_candidates,
        'test_papers': test_papers,
        'title': f"Drive: {drive.title}"
    }
    return render(request, 'recruitment/drive_detail.html', context)


# @login_required
# @transaction.atomic
# def drive_edit_view(request, drive_id):
#     """Edit an existing recruitment drive"""
#     drive = get_object_or_404(RecruitmentDrive, pk=drive_id, created_by=request.user)
    
#     if request.method == 'POST':
#         form = RecruitmentDriveForm(request.POST, instance=drive)
#         if form.is_valid():
#             form.save()
#             messages.success(request, "Drive updated successfully!")
#             return redirect('drive_detail', drive_id=drive.id)
#     else:
#         form = RecruitmentDriveForm(instance=drive)
    
#     context = {'form': form, 'drive': drive, 'title': f'Edit: {drive.title}'}
#     return render(request, 'recruitment/drive_form.html', context)
@login_required
@transaction.atomic
def drive_edit_view(request, drive_id):
    """Edit an existing recruitment drive"""
    drive = get_object_or_404(RecruitmentDrive, pk=drive_id, created_by=request.user)
    
    if request.method == 'POST':
        form = RecruitmentDriveForm(request.POST, instance=drive)
        if form.is_valid():
            updated_drive = form.save(commit=False)
            
            # ✅ Prevent manually setting status to COMPLETED if positions aren't filled
            if updated_drive.drive_status == 'COMPLETED' and updated_drive.filled_positions < updated_drive.total_positions:
                messages.error(request, "Cannot mark drive as COMPLETED until all positions are filled!")
                return redirect('drive_edit', drive_id=drive.id)
            
            updated_drive.save()
            form.save_m2m()
            
            messages.success(request, "Drive updated successfully!")
            return redirect('drive_detail', drive_id=drive.id)
    else:
        form = RecruitmentDriveForm(instance=drive)
    
    context = {'form': form, 'drive': drive, 'title': f'Edit: {drive.title}'}
    return render(request, 'recruitment/drive_form.html', context)


@login_required
@require_POST
def drive_delete_view(request, drive_id):
    """Soft delete a drive"""
    drive = get_object_or_404(RecruitmentDrive, pk=drive_id, created_by=request.user)
    
    # Check if any candidates are hired
    if drive.applications.filter(overall_status='HIRED').exists():
        return JsonResponse({
            'status': 'error',
            'message': 'Cannot delete drive with hired candidates.'
        }, status=400)
    
    drive.drive_status = 'CANCELLED'
    drive.is_public_link_active = False
    drive.save(update_fields=['drive_status', 'is_public_link_active'])
    
    return JsonResponse({
        'status': 'success',
        'message': 'Drive cancelled successfully.'
    })


@login_required
@require_POST
def toggle_drive_status(request, drive_id):
    """Toggle drive status (OPEN/PAUSED)"""
    drive = get_object_or_404(RecruitmentDrive, pk=drive_id, created_by=request.user)
    
    if drive.drive_status == 'OPEN':
        drive.drive_status = 'IN_PROGRESS'
        drive.is_public_link_active = False
    elif drive.drive_status in ['DRAFT', 'IN_PROGRESS']:
        drive.drive_status = 'OPEN'
        drive.is_public_link_active = True
    
    drive.save(update_fields=['drive_status', 'is_public_link_active'])
    
    return JsonResponse({
        'status': 'success',
        'drive_status': drive.drive_status,
        'is_public_link_active': drive.is_public_link_active
    })


# Candidate Management Views

@login_required
def drive_candidates_view(request, drive_id):
    """List all candidates for a drive with filters"""
    drive = get_object_or_404(RecruitmentDrive, pk=drive_id, created_by=request.user)
    
    stage_filter = request.GET.get('stage', 'all')
    status_filter = request.GET.get('status', 'all')
    
    candidates_query = drive.applications.all()
    
    if stage_filter != 'all':
        candidates_query = candidates_query.filter(current_stage=stage_filter.upper())
    
    if status_filter != 'all':
        candidates_query = candidates_query.filter(overall_status=status_filter.upper())
    
    candidates = candidates_query.order_by('-applied_at')
    
    paginator = Paginator(candidates, 20)
    page_number = request.GET.get('page')
    candidates_page = paginator.get_page(page_number)
    
    context = {
        'drive': drive,
        'candidates': candidates_page,
        'selected_stage': stage_filter,
        'selected_status': status_filter,
        'title': f'Candidates: {drive.title}'
    }
    return render(request, 'recruitment/candidates_list.html', context)


@login_required
def candidate_detail_view(request, drive_id, candidate_id):
    """Detailed view of a single candidate"""
    drive = get_object_or_404(RecruitmentDrive, pk=drive_id, created_by=request.user)
    candidate = get_object_or_404(CandidateApplication, pk=candidate_id, recruitment_drive=drive)
    
    # Get all test attempts
    test_attempts = candidate.test_attempts.all().order_by('start_time')
    
    # Calculate aggregate score if needed
    if not candidate.aggregate_score:
        candidate.calculate_aggregate_score()
    
    context = {
        'drive': drive,
        'candidate': candidate,
        'test_attempts': test_attempts,
        'title': f'Candidate: {candidate.full_name}'
    }
    return render(request, 'recruitment/candidate_detail.html', context)


@login_required
@require_POST
def update_candidate_stage(request, candidate_id):
    """Update a candidate's stage"""
    try:
        data = json.loads(request.body)
        candidate = get_object_or_404(CandidateApplication, pk=candidate_id)
        
        new_stage = data.get('new_stage')
        notes = data.get('notes', '')
        rejection_reason = data.get('rejection_reason', '')
        
        # Move candidate to new stage
        candidate.move_to_stage(new_stage, updated_by=request.user, reason=rejection_reason)
        
        if notes:
            candidate.notes = notes
            candidate.save(update_fields=['notes'])
        
        # TODO: Send email notification to candidate
        
        return JsonResponse({
            'status': 'success',
            'message': f'Candidate moved to {new_stage}',
            'new_stage': candidate.current_stage,
            'overall_status': candidate.overall_status
        })
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
@require_POST
def bulk_update_stages(request):
    """Bulk update candidate stages"""
    try:
        data = json.loads(request.body)
        candidate_ids = data.get('candidate_ids', [])
        new_stage = data.get('new_stage')
        
        success_count = 0
        error_count = 0
        
        for cid in candidate_ids:
            try:
                candidate = CandidateApplication.objects.get(pk=cid)
                candidate.move_to_stage(new_stage, updated_by=request.user)
                success_count += 1
            except Exception:
                error_count += 1
        
        return JsonResponse({
            'status': 'success',
            'message': f'{success_count} candidates updated, {error_count} errors'
        })
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# Public Application View

def candidate_apply_view(request, drive_uuid):
    """Public page for candidates to apply"""
    drive = get_object_or_404(RecruitmentDrive, drive_uuid=drive_uuid)
    
    # Check if drive is accepting applications
    if not drive.is_accepting_applications:
        return render(request, 'recruitment/drive_closed.html', {'drive': drive}, status=403)
    
    if request.method == 'POST':
        form = CandidateApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save(commit=False)
            application.recruitment_drive = drive
            application.save()
            
            # TODO: Send confirmation email
            
            messages.success(request, "Application submitted successfully!")
            return redirect('recruitment_apply_success', drive_uuid=drive_uuid)
    else:
        form = CandidateApplicationForm()
    
    context = {
        'drive': drive,
        'form': form,
        'title': f'Apply: {drive.position}'
    }
    return render(request, 'recruitment/candidate_application_form.html', context)


# Analytics & Export

@login_required
def drive_analytics_view(request, drive_id):
    """Show analytics for a drive"""
    drive = get_object_or_404(RecruitmentDrive, pk=drive_id, created_by=request.user)
    
    # Calculate stats
    total_applications = drive.applications.count()
    hired_count = drive.applications.filter(overall_status='HIRED').count()
    rejected_count = drive.applications.filter(overall_status='REJECTED').count()
    active_count = drive.applications.filter(overall_status='ACTIVE').count()
    
    # Stage breakdown
    stage_counts = drive.get_stage_wise_count()
    
    # Average score
    avg_score = drive.applications.filter(
        aggregate_score__isnull=False
    ).aggregate(Avg('aggregate_score'))['aggregate_score__avg']
    
    context = {
        'drive': drive,
        'total_applications': total_applications,
        'hired_count': hired_count,
        'rejected_count': rejected_count,
        'active_count': active_count,
        'stage_counts': stage_counts,
        'average_score': round(avg_score, 2) if avg_score else None,
        'title': f'Analytics: {drive.title}'
    }
    return render(request, 'recruitment/drive_analytics.html', context)


@login_required
def export_drive_data(request, drive_id):
    """Export all candidate data as CSV"""
    drive = get_object_or_404(RecruitmentDrive, pk=drive_id, created_by=request.user)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="drive_{drive.id}_candidates.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Name', 'Email', 'Phone', 'Stage', 'Status', 'Aggregate Score', 'Applied Date'])
    
    for candidate in drive.applications.all():
        writer.writerow([
            candidate.full_name,
            candidate.email,
            candidate.phone_number,
            candidate.get_current_stage_display(),
            candidate.get_overall_status_display(),
            candidate.aggregate_score or 'N/A',
            candidate.applied_at.strftime('%Y-%m-%d')
        ])
    
    return response


import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404

# @login_required
# @require_POST
# def toggle_drive_link(request, drive_id):
#     """Toggle public link for recruitment drive"""
#     try:
#         drive = get_object_or_404(RecruitmentDrive, id=drive_id, created_by=request.user)
        
#         data = json.loads(request.body)
#         action = data.get('action')
        
#         if action == 'activate':
#             drive.is_public_link_active = True
#             # ✅ CHANGE STATUS TO OPEN
#             if drive.drive_status == 'DRAFT':
#                 drive.drive_status = 'OPEN'
#             drive.save()

#             message = 'Public link activated! Drive is now OPEN.'
            
#         elif action == 'deactivate':
#             drive.is_public_link_active = False
#             message = 'Public link deactivated!'
#         else:
#             return JsonResponse({'success': False, 'message': 'Invalid action'}, status=400)
        
#         drive.save()
#         return JsonResponse({'success': True, 'message': message})
        
#     except Exception as e:
#         return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@require_POST
def toggle_drive_link(request, drive_id):
    """Toggle public link for recruitment drive"""
    try:
        drive = get_object_or_404(RecruitmentDrive, id=drive_id, created_by=request.user)
        
        data = json.loads(request.body)
        action = data.get('action')
        
        if action == 'activate':
            drive.is_public_link_active = True
            if drive.drive_status == 'DRAFT':
                drive.drive_status = 'OPEN'
            drive.save()
            message = 'Public link activated! Drive is now OPEN.'
            
        elif action == 'deactivate':
            drive.is_public_link_active = False
            drive.save()
            message = 'Public link deactivated!'
        else:
            return JsonResponse({'success': False, 'message': 'Invalid action'}, status=400)
        
        return JsonResponse({'success': True, 'message': message})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


# app/views.py (somewhere after save_paper or before list_papers)

@login_required
def get_paper_details_json(request, paper_id):
    """
    Returns a single QuestionPaper's details and structure (sections/questions count) 
    in JSON format for pre-filling the assessment configuration page (Step 2).
    """
    try:
        # User only gets to see their own papers
        paper = get_object_or_404(QuestionPaper, pk=paper_id, created_by=request.user)
        
        # 1. Collect Step 2 Data
        sections_data = {}
        for section in paper.paper_sections.all().order_by('order'):
            # The client-side requires the section name and the count of questions
            sections_data[section.title] = section.questions.count()
            
        # 2. Get the Department ID (assuming you have a department_id field or can derive it)
        # Note: Since the QuestionPaper model does not seem to directly link to Department ID 
        # (it only stores department_name), we will try to infer it. 
        # If Department model has a unique name, we can do this:
        department_id = None
        try:
            department_id = Department.objects.get(name=paper.department_name).id
        except Department.DoesNotExist:
            pass # Keep it None if department is not found
            
        # 3. Format the JSON Response
        return JsonResponse({
            "status": "success",
            "id": paper.id,
            "title": paper.title,
            "duration": paper.duration,
            "cutoff_score": paper.cutoff_score,
            "department_id": department_id, # Frontend needs this to re-render sections
            "sections": sections_data, # {'Technical': 10, 'Aptitude': 5}
        })

    except QuestionPaper.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Paper not found."}, status=404)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)




# app/views.py

# ... (Existing imports: import json, transaction, csrf_exempt, CandidateApplicationForm, CandidateApplication, messages, get_object_or_404, etc.)
from django.views.decorators.http import require_http_methods 
from django.core.exceptions import ValidationError 


from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json # for reading request body in case of non-form submission, though not strictly needed here

from .models import QuestionPaper # Ensure this is imported
from .forms import CandidateApplicationForm

# app/views.py

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import QuestionPaper, CandidateApplication
from .forms import CandidateApplicationForm

# app/views.py - Updated submit_personal_info_application

import json
from django.shortcuts import get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.db import IntegrityError




@require_http_methods(["POST"])
def submit_personal_info_application(request, paper_id):
    """
    Handles AJAX submission of the personal information form for a specific QuestionPaper.
    """
    try:
        # 1. Validate Paper ID and availability
        paper = get_object_or_404(QuestionPaper, pk=paper_id)
        
        # 2. Prepare Form Data and Validate
        post_data = request.POST.copy()
        candidate_type = post_data.get('candidateType') # e.g., 'fresher' or 'experienced'

        form = CandidateApplicationForm(post_data, request.FILES)
        
        # 3. Handle Duplicate Check (Server-side)
        if form.is_valid():
            email = form.cleaned_data['email'].lower()
        
            
            # Check for duplicate application against the specific paper
            if CandidateApplication.objects.filter(email=email, linked_paper=paper).exists():
                 return JsonResponse(
                    {"message": f"You have already submitted an application for the job posting: {paper.job_title}.", "errors": {"email": ["You have already applied for this job."]}},
                    status=409 # Conflict status code
                )
            
            # 4. Save the Application and Apply Fixes ⭐ FIXED LOGIC START ⭐
            application = form.save(commit=False)
            
            # --- FIX 1: Map candidateType (string) to is_experienced (Boolean) ---
            is_experienced_candidate = (candidate_type == 'experienced')
            application.is_experienced = is_experienced_candidate
            
            # --- FIX 2: Clear experienced-only fields if candidate is a Fresher ---
            if not is_experienced_candidate:
                # Assuming these fields are nullable or accept 0 in the model
                application.total_experience = None 
                application.current_ctc = None
                application.current_ctc_rate = None
                application.notice_period = "" 
            # ⭐ FIXED LOGIC END ⭐

            # Set relationships and initial status
            application.linked_paper = paper
            
            if paper.recruitment_drive:
                application.recruitment_drive = paper.recruitment_drive
            
            application.current_stage = CandidateApplication.CandidateStage.APPLIED
            application.overall_status = CandidateApplication.ApplicationStatus.ACTIVE
            
            application.save()
            
            return JsonResponse(
                {"message": "Application submitted successfully.", "application_id": application.id},
                status=201 # Created
            )
        else:
            # 5. Return Form Validation Errors (Map to HTML IDs for JS to display)
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = error_list[0] 
            
            # Re-map Django field names to HTML IDs for frontend display
            error_mapping = {
                'full_name': 'fullName', 
                'phone_number': 'mobile', 
                'resume_file': 'resume', 
                'photo_file': 'photo',
                'total_experience': 'experience',
                'cover_letter': 'coverLetter',
                'current_ctc': 'currentCTC',
                'current_ctc_rate': 'currentCTCRate',
                'expected_ctc': 'expectedCTC',
                'expected_ctc_rate': 'expectedCTCRate',
                'notice_period': 'noticePeriod',
                # 'email' and 'skills' already match their HTML IDs
            }
            
            response_errors = {}
            for field, msg in errors.items():
                html_name = error_mapping.get(field, field)
                response_errors[html_name] = [msg]

            return JsonResponse(
                {"message": "Validation Failed", "errors": response_errors},
                status=400 # Bad Request
            )

    except QuestionPaper.DoesNotExist:
        return JsonResponse(
            {"message": "The specified job posting/paper ID was not found."},
            status=404
        )
    except Exception as e:
        print(f"Server Error during application submission: {e}")
        return JsonResponse(
            {"message": f"An unexpected server error occurred: {e}"},
            status=500
        )


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from .models import QuestionPaper, CandidateApplication

@login_required
def paper_applications_view(request, paper_id):
    """
    View to see all candidate applications for a specific QuestionPaper
    """
    paper = get_object_or_404(
        QuestionPaper, 
        pk=paper_id, 
        created_by=request.user
    )
    
    # Filter applications
    stage_filter = request.GET.get('stage', 'all')
    status_filter = request.GET.get('status', 'all')
    
    # Get all applications linked to this paper
    applications_query = CandidateApplication.objects.filter(
        linked_paper=paper
    ).order_by('-applied_at')
    
    # Apply filters
    if stage_filter != 'all':
        applications_query = applications_query.filter(
            current_stage=stage_filter.upper()
        )
    
    if status_filter != 'all':
        applications_query = applications_query.filter(
            overall_status=status_filter.upper()
        )
    
    # Pagination
    paginator = Paginator(applications_query, 20)
    page_number = request.GET.get('page')
    applications = paginator.get_page(page_number)
    
    # Statistics
    total_applications = CandidateApplication.objects.filter(
        linked_paper=paper
    ).count()
    
    active_count = CandidateApplication.objects.filter(
        linked_paper=paper,
        overall_status='ACTIVE'
    ).count()
    
    hired_count = CandidateApplication.objects.filter(
        linked_paper=paper,
        overall_status='HIRED'
    ).count()
    
    context = {
        'paper': paper,
        'applications': applications,
        'total_applications': total_applications,
        'active_count': active_count,
        'hired_count': hired_count,
        'selected_stage': stage_filter,
        'selected_status': status_filter,
        'title': f'Applications for {paper.job_title}'
    }
    
    return render(request, 'recruitment/paper_applications.html', context)


@login_required
def application_detail_view(request, application_id):
    """
    Detailed view of a single candidate application
    """
    application = get_object_or_404(
        CandidateApplication,
        pk=application_id
    )
    
    # Verify the user owns the linked paper
    if application.linked_paper and application.linked_paper.created_by != request.user:
        return HttpResponseForbidden("You don't have permission to view this application.")
    
    context = {
        'application': application,
        'paper': application.linked_paper,
        'title': f'Application: {application.full_name}'
    }
    
    return render(request, 'recruitment/application_detail.html', context)


@login_required
def export_paper_applications_csv(request, paper_id):
    """
    Export all applications for a paper as CSV
    """
    paper = get_object_or_404(
        QuestionPaper,
        pk=paper_id,
        created_by=request.user
    )
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="applications_{paper.job_title}_{paper.id}.csv"'
    
    writer = csv.writer(response)
    
    # Header row
    writer.writerow([
        'Full Name', 'Email', 'Phone', 
        'Experience Type', 'Total Experience (Years)',
        'Current CTC', 'Expected CTC',
        'Skills', 'Location', 'Referral Source',
        'Stage', 'Status', 'Applied Date'
    ])
    
    # Data rows
    applications = CandidateApplication.objects.filter(
        linked_paper=paper
    ).order_by('-applied_at')
    
    for app in applications:
        writer.writerow([
            app.full_name,
            app.email,
            app.phone_number,
            'Experienced' if app.is_experienced else 'Fresher',
            app.total_experience or 0,
            app.current_ctc or 'N/A',
            app.expected_ctc or 'N/A',
            app.skills or 'N/A',
            app.current_location or 'N/A',
            app.referral_source or 'N/A',
            app.get_current_stage_display(),
            app.get_overall_status_display(),
            app.applied_at.strftime('%Y-%m-%d %H:%M')
        ])
    
    return response



@login_required
@require_POST
@transaction.atomic
def create_interview_round(request):
    """
    Creates a placeholder entry in QuestionPaper for an Interview Round
    and returns a unique shareable **application link** (using paper_id).
    """
    try:
        data = json.loads(request.body)
        rounds_raw = data.get("rounds")
        round_title = 'Interview Round'
        
        # ... (Round title logic) ...
        if rounds_raw == '2': round_title = 'Technical Interview (R1)'
        elif rounds_raw == '3': round_title = 'Technical Interview (R2)'
        elif rounds_raw == '4': round_title = 'HR Round (Final)'
        elif rounds_raw == '1': 
            return JsonResponse({"status": "error", "message": "Assessment rounds must use generate_questions endpoint."}, status=400)
        else: round_title = f'Round {rounds_raw}'
        
        # Get Department Name from ID
        department_name = Department.objects.get(id=data.get("departmentId")).name
        
        # ... (Paper creation logic) ...
        paper = QuestionPaper.objects.create(
            created_by=request.user,
            title=f"{data.get('job_title', 'N/A')} - {round_title}",
            job_title=data.get("job_title", ""),
            department_name=department_name,
            min_exp=data.get("min_exp", 0),
            max_exp=data.get("max_exp", 0),
            duration=0, 
            is_active=True,
            is_public_active=True, # 💡 CHANGE: Apply link ke liye ise True rakhein
            is_private_link_active=False,
            cutoff_score=0, 
            skills_list=data.get("skills", ""),
            total_questions=0,
            is_interview_round=True,
            # Added Logistic fields
            job_location=data.get("job_location", ""), 
            job_type=data.get("job_type", ""),
            positions=data.get("positions", ""),
            rounds=data.get("rounds", ""),
            pay_scale=data.get("pay_scale", ""),
            end_date=data.get("end_date", None),
        )

        # 💡 CRITICAL CHANGE: Interview Application Link generate karein
        # Link 'interview_candidate_apply_view' ko point karega
        interview_apply_url = reverse(
            "interview_candidate_apply", kwargs={"paper_id": paper.id}
        )
        share_link_url = request.build_absolute_uri(interview_apply_url)
        
        # Success response wapas bhej dein
        return JsonResponse({
            "status": "success",
            "title": paper.title, 
            "paper_id": paper.id,
            "share_link": share_link_url, # <--- Frontend ab yeh link use karega
            "message": "Interview round created successfully. Share the application link with candidates."
        }, status=201)

    except Department.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Invalid Department ID."}, status=400)
    except Exception as e:
        print(f"Error creating interview round: {str(e)}")
        return JsonResponse({"status": "error", "message": f"Server Error: {str(e)}"}, status=500)


@transaction.atomic 
def interview_candidate_apply_view(request, paper_id):
    """Public page for candidates to apply based on a QuestionPaper link (Interview)."""
    
    paper = get_object_or_404(QuestionPaper, pk=paper_id)
    
    if not paper.is_interview_round:
        return render(request, 'recruitment/drive_closed.html', {'message': 'This link is for a written assessment, not a candidate application form.'}, status=403)
        
    if not paper.is_public_active:
        return render(request, 'recruitment/drive_closed.html', {'message': 'The application link for this interview round is currently inactive.'}, status=403)

    if request.method == 'POST':
        # 💡 IMPORTANT: request.POST को mutable बनाने की ज़रूरत नहीं, सीधे form में पास करें
        
        # CandidateApplicationForm को request.POST और request.FILES के साथ instantiate करें
        # Note: 'initial' सिर्फ GET request के लिए होता है, POST के लिए नहीं
        form = CandidateApplicationForm(request.POST, request.FILES) 
        
        if form.is_valid():
            email = form.cleaned_data['email']

            # Duplicate Check: Check for application with same email linked to this paper
            if CandidateApplication.objects.filter(email__iexact=email, linked_paper=paper).exists():
                 messages.error(request, "An application with this email already exists for this interview round.")
                 return render(request, 'recruitment/interview_application_form.html', {'paper': paper, 'form': form, 'title': f'Apply: {paper.job_title}'})


            application = form.save(commit=False)
            
            # ⭐ CRITICAL FIX: QuestionPaper (Interview Round) को CandidateApplication से लिंक करें
            application.linked_paper = paper
            
            # Initial stage set करें (Optional, पर अच्छा है)
            application.current_stage = CandidateApplication.CandidateStage.APPLIED
            application.overall_status = CandidateApplication.ApplicationStatus.ACTIVE
            
            application.save()
            form.save_m2m() # M2M data (agar form mein ho) save karein
            
            messages.success(request, f"Application for {paper.job_title} submitted successfully! We will connect with you soon.")
            
            # Success screen dikhayen
            return render(request, 'recruitment/candidate_application_success.html', {'paper': paper, 'title': 'Application Success', 'candidate': application})
        else:
            # Form validation fail hone par error message dikhayen
            messages.error(request, "Please correct the errors below.")
            
    else:
        # GET request: Form को initialize करे
        form = CandidateApplicationForm(initial={
            'full_name': request.GET.get('full_name', ''),
            'email': request.GET.get('email', '') 
        })

    context = {
        'paper': paper,
        'form': form,
        'title': f'Apply: {paper.job_title}'
    }
    return render(request, 'recruitment/interview_application_form.html', context)
    """Public page for candidates to apply based on a QuestionPaper link (Interview)."""
    
    paper = get_object_or_404(QuestionPaper, pk=paper_id)
    
    # ... (Error checks for paper.is_interview_round and paper.is_public_active remain the same) ...
    if not paper.is_interview_round:
        return render(request, 'recruitment/drive_closed.html', {'message': 'This link is for a written assessment, not a candidate application form.'}, status=403)
        
    if not paper.is_public_active:
        return render(request, 'recruitment/drive_closed.html', {'message': 'The application link for this interview round is currently inactive.'}, status=403)

    if request.method == 'POST':
        # 💡 IMPORTANT: request.POST ko mutable banao tak ki hum data modify kar sakein
        post_data = request.POST.copy()
        
        # 💡 HTML Form fields ko Model fields se map karein
        # HTML: fullName -> Model: full_name
        # HTML: mobile -> Model: phone_number
        post_data['full_name'] = post_data.get('fullName')
        post_data['phone_number'] = post_data.get('mobile')
        
        # HTML: resume -> Model: resume_file
        # HTML: photo (IGNORED)
        
        # CandidateApplicationForm ko prepare kiye gaye data ke saath instantiate karein
        # 'recruitment_drive' field ko exclude kar rahe hain kyunki QuestionPaper se link kar rahe hain
        form = CandidateApplicationForm(post_data, request.FILES) 
        
        if form.is_valid():
            # Check for duplicate application (optional but recommended)
            if CandidateApplication.objects.filter(email=form.cleaned_data['email']).exists():
                 messages.error(request, "An application with this email already exists.")
                 return render(request, 'recruitment/interview_application_form.html', {'paper': paper, 'form': form, 'title': f'Apply: {paper.job_title}'})

            application = form.save(commit=False)
            
            # 💡 CRITICAL: Recruitment Drive ya Question Paper ko link karein
            # Hum yahan QuestionPaper ko link kar rahe hain (agar model mein field ho)
            # Lekin CandidateApplication model mein QuestionPaper ke liye koi FK nahi hai.
            # Isliye, hum sirf data save kar rahe hain. 
            # Agar RecruitmentDrive se link karna ho toh pehle drive banana hoga.

            # Safest option: Sirf data save karein
            application.save()
            
            # CRITICAL: Is user ko TestRegistration mein bhi save karna hoga agar baad mein is user ko test dena ho.
            # Filhaal, hum TestRegistration ko bypass kar rahe hain kyonki yeh interview round hai.
            # Agar future mein QuestionPaper se link karna ho, toh CandidateApplication model mein ek FK field add karein.
            
            # Success screen dikhayen
            messages.success(request, f"Application for {paper.job_title} submitted successfully! We will connect with you soon.")
            
            # Reload page to show success screen (like the HTML does)
            return render(request, 'recruitment/candidate_application_success.html', {'paper': paper, 'title': 'Application Success', 'candidate': application})
        else:
            # Form validation fail hone par error message dikhayen
            messages.error(request, "Please correct the errors below.")

    else:
        # GET request: Form ko initialize karein
        form = CandidateApplicationForm(initial={
            'full_name': request.GET.get('full_name', ''), # Agar URL mein koi prefill ho
            'email': request.GET.get('email', '') 
        })

    context = {
        'paper': paper,
        'form': form,
        'title': f'Apply: {paper.job_title}'
    }
    return render(request, 'recruitment/interview_application_form.html', context)
    """Public page for candidates to apply based on a QuestionPaper link (Interview)."""
    
    # Paper ko fetch karein aur ensure karein ki yeh interview round hai
    paper = get_object_or_404(QuestionPaper, pk=paper_id)
    
    if not paper.is_interview_round:
        # Agar galti se written test ka link use kiya, toh error de dein
        return render(request, 'recruitment/drive_closed.html', {'message': 'This link is for a written assessment, not a candidate application form.'}, status=403)
        
    # Check if the public link is active (optional, but good practice)
    if not paper.is_public_active:
        return render(request, 'recruitment/drive_closed.html', {'message': 'The application link for this interview round is currently inactive.'}, status=403)

    if request.method == 'POST':
        # CandidateApplicationForm mein paper_id ko pass karne ke liye
        form = CandidateApplicationForm(request.POST, request.FILES, initial={'paper_id': paper.id})
        
        if form.is_valid():
            application = form.save(commit=False)
            
            # Note: Assuming CandidateApplication model has fields to store data.
            # Agar CandidateApplication ko QuestionPaper se link karna hai, toh model mein field add karein.
            # Filhaal, hum sirf form fill karwa rahe hain.
            
            application.save()
            
            messages.success(request, f"Application for {paper.job_title} submitted successfully!")
            # Assuming a success template exists
            return render(request, 'recruitment/candidate_application_success.html', {'paper': paper, 'title': 'Application Success'})
    else:
        # Form ko initialize karein
        form = CandidateApplicationForm(initial={'job_title': paper.job_title})

    context = {
        'paper': paper,
        'form': form,
        'title': f'Apply: {paper.job_title}'
    }
    return render(request, 'recruitment/interview_application_form.html', context) # <--- Naya template