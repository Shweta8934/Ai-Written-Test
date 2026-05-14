from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.http import HttpResponse, JsonResponse  # <-- JsonResponse imported
from django.utils import timezone  # <-- timezone imported
from datetime import timedelta  # <-- timedelta imported
import re

# IMPORTS
from app.models import QuestionPaper, Question
from .models import TestRegistration, UserResponse
from .forms import TestRegistrationForm
from django.urls import reverse  # Required for redirecting using named URLs

from openai import OpenAI
from django.conf import settings
import json
from django.views.decorators.csrf import csrf_exempt

# --- HELPER FUNCTION FOR FLOW CONTROL ---


def get_session_key(link_id):
    """Generates the unique session key for this test link."""
    return f"test_status_{link_id}"


def check_flow_and_redirect(request, link_id, current_stage_name):
    """
    Checks the user's progress status using the session and registration completion status.
    Returns a HttpResponseRedirect object if a redirect is needed, otherwise returns None.

    Stages:
    1. user_register_link
    2. user_instructions
    3. user_test
    4. user_already_submitted (final state)
    """
    session_key = get_session_key(link_id)
    session_status = request.session.get(session_key, "not_started")

    # Define the strict flow map: where should the user be coming from?
    # Key: Current view name, Value: Required session status to be here
    FLOW_SEQUENCE = [
        "user_register_link",  # not_started
        "user_instructions",  # registered
        "user_test",  # instructed (after POST on instructions)
        "user_already_submitted",  # submitted (final state, checked via DB)
    ]

    current_index = FLOW_SEQUENCE.index(current_stage_name)

    # 1. High Priority Check: Already Submitted (via DB)
    registration_id = request.session.get("current_registration_id")
    if registration_id:
        try:
            reg = TestRegistration.objects.get(pk=registration_id, is_completed=True)
            # If submitted, always go to the final page, unless we are already there.
            if current_stage_name != "user_already_submitted":
                return redirect("test:user_already_submitted")
        except TestRegistration.DoesNotExist:
            pass

    # 2. Flow Enforcement Check (for backward/forward jumps)
    if current_stage_name == "user_register_link":
        # If they successfully registered, push them forward.
        if session_status == "registered":
            return redirect("test:user_instructions", link_id=link_id)
        # If they somehow got to 'instructed' or 'in_progress', send them to test.
        if session_status in ["instructed", "in_progress"]:
            return redirect("test:user_test", link_id=link_id)

    elif current_stage_name == "user_instructions":
        # Must be 'registered' to access instructions.
        if session_status == "not_started":
            return redirect("test:user_register_link", link_id=link_id)
        # If they already accepted instructions, push them to the test.
        if session_status in ["instructed", "in_progress"]:
            return redirect("test:user_test", link_id=link_id)

    elif current_stage_name == "user_test":
        # Must be 'instructed' to access the test.
        if session_status == "not_started":
            return redirect("test:user_register_link", link_id=link_id)
        if session_status == "registered":
            return redirect("test:user_instructions", link_id=link_id)

    # For 'user_already_submitted', we rely on the DB check above.

    return None  # No redirect needed, proceed to view logic


# --- BACKEND TIMER API VIEW ---


def get_time_remaining_api(request, link_id):
    """
    Calculates and returns the time remaining for the currently active test registration.
    This is the backend source of truth for the timer.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    registration_id = request.session.get("current_registration_id")
    if not registration_id:
        # अगर session में registration ID नहीं है, मतलब test flow शुरू नहीं हुआ है
        return JsonResponse({"error": "Registration not found"}, status=403)

    try:
        paper_id = int(link_id)
        paper = get_object_or_404(QuestionPaper, pk=paper_id)

        # Registration ऑब्जेक्ट प्राप्त करें जो in-progress है (is_completed=False)
        registration = get_object_or_404(
            TestRegistration,
            pk=registration_id,
            question_paper=paper,
            is_completed=False,
        )
    except Exception:
        # अगर registration already complete है या कोई और error है
        return JsonResponse({"remaining_seconds": 0, "time_up": True})

    # परीक्षा की अवधि मिनटों में
    duration_minutes = paper.duration

    # समाप्ति का अनुमानित समय (start_time + duration)
    expected_end_time = registration.start_time + timedelta(minutes=duration_minutes)

    # शेष समय की गणना
    time_remaining = expected_end_time - timezone.now()

    remaining_seconds = int(time_remaining.total_seconds())

    # --- Time Up/Auto-Submission Check ---
    if remaining_seconds <= 0:

        # DB में mark करें और session clean up करें (Auto-Submit Logic)
        with transaction.atomic():
            registration.is_completed = True
            registration.save()

            if "current_registration_id" in request.session:
                del request.session["current_registration_id"]

            # Set final session status
            request.session[get_session_key(link_id)] = "submitted"
            request.session.modified = True

        return JsonResponse({"remaining_seconds": 0, "time_up": True})

    return JsonResponse({"remaining_seconds": remaining_seconds, "time_up": False})


@csrf_exempt
def run_code_ai(request):
    """
    Simulates code execution using Gemini via OpenRouter.
    Provides a unified way to 'run' all supported languages.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body)
        code = data.get("code")
        language = data.get("language", "python")
        question_text = data.get("question_text", "")

        if not code:
            return JsonResponse({"error": "No code provided"}, status=400)

        prompt = f"""
        Act as a high-performance code execution engine and compiler.
        
        TASK:
        Execute the following {language} code and provide the output exactly as it would appear in a terminal/console.
        
        CONTEXT (Question being solved):
        {question_text}
        
        CODE TO EXECUTE:
        ```{language}
        {code}
        ```
        
        RULES:
        1. If the code is correct, return ONLY the output of the execution.
        2. If there are syntax errors or runtime errors, return the error message exactly as the compiler/interpreter would.
        3. Do NOT provide any explanations, comments, or markdown formatting in your response.
        4. If the code takes input, assume reasonable defaults based on the question context.
        5. If the code prints nothing, return "Code executed successfully (no output)".
        
        Return ONLY the terminal output:
        """

        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENAI_API_KEY.strip(),
            default_headers={
                "HTTP-Referer": "http://10.0.0.17:8000",
                "X-Title": "AI Written Test Platform",
            }
        )

        response = client.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=[
                {"role": "system", "content": "You are a terminal emulator that executes code and returns only the output or errors."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0, # Keep it deterministic
        )

        output = response.choices[0].message.content.strip()
        
        # Clean up any accidental markdown
        if output.startswith("```"):
            output = re.sub(r"```[^\n]*\n", "", output)
            output = output.replace("```", "")

        return JsonResponse({"output": output})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# --- VIEWS START HERE ---


def user_register_view(request, link_id):
    """Handles test taker registration."""

    # ... (rest of user_register_view remains unchanged) ...

    # --- FLOW CHECK ---
    redirect_response = check_flow_and_redirect(request, link_id, "user_register_link")
    if redirect_response:
        return redirect_response
    # --- END FLOW CHECK ---

    try:
        paper_id = int(link_id)
        # Check that the paper exists AND is public
        paper = get_object_or_404(QuestionPaper, pk=paper_id, is_public_active=True)
    except (ValueError, QuestionPaper.DoesNotExist):
        messages.error(request, "The test link is invalid or deactivated.")
        return redirect("home")

    # Previous logic to check existing session registration ID and redirect to instructions.
    registration_id = request.session.get("current_registration_id")
    if registration_id:
        try:
            # Check if registration exists and is NOT completed
            reg = TestRegistration.objects.get(
                pk=registration_id, question_paper=paper, is_completed=False
            )
            return redirect("test:user_instructions", link_id=link_id)
        except TestRegistration.DoesNotExist:
            pass

    if request.method == "POST":
        form = TestRegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']

            # ✅ Check BEFORE saving to avoid broken PostgreSQL transactions
            existing_reg = TestRegistration.objects.filter(
                email=email,
                question_paper=paper
            ).first()

            if existing_reg:
                # Registration already exists (e.g. from job application)
                if existing_reg.is_completed:
                    return redirect("test:user_already_submitted")
                # Resume the incomplete test
                request.session["current_registration_id"] = existing_reg.id
                request.session[get_session_key(link_id)] = "registered"
                request.session.modified = True
                return redirect("test:user_instructions", link_id=link_id)

            # New registration — save to DB
            try:
                registration = form.save(commit=False)
                registration.question_paper = paper
                registration.save()

                request.session["current_registration_id"] = registration.id
                request.session[get_session_key(link_id)] = "registered"
                request.session.modified = True

                messages.success(
                    request, "Registration successful. Please read instructions."
                )
                return redirect("test:user_instructions", link_id=link_id)

            except Exception as e:
                # Race condition fallback (two requests at the same time)
                fallback_reg = TestRegistration.objects.filter(
                    email=email, question_paper=paper
                ).first()
                if fallback_reg:
                    if fallback_reg.is_completed:
                        return redirect("test:user_already_submitted")
                    request.session["current_registration_id"] = fallback_reg.id
                    request.session[get_session_key(link_id)] = "registered"
                    request.session.modified = True
                    return redirect("test:user_instructions", link_id=link_id)

                messages.error(
                    request,
                    "An error occurred during registration. Please try again.",
                )
                return redirect("test:user_register_link", link_id=link_id)

    else:
        form = TestRegistrationForm()

    context = {
        "form": form,
        "link_id": link_id,
        "paper_title": paper.title,
    }
    response = render(request, "user_test/register.html", context)
    # ************************************************
    # * NEW: AGGRESSIVE CACHING HEADERS ADDED HERE *
    # ************************************************
    response["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"

    return response


def user_instruction_view(request, link_id):
    """Shows test details and instructions before starting."""

    # ... (rest of user_instruction_view remains unchanged) ...

    # --- FLOW CHECK ---
    redirect_response = check_flow_and_redirect(request, link_id, "user_instructions")
    if redirect_response:
        return redirect_response
    # --- END FLOW CHECK ---

    try:
        paper_id = int(link_id)
        paper = get_object_or_404(QuestionPaper, pk=paper_id, is_public_active=True)
    except (ValueError, QuestionPaper.DoesNotExist):
        return redirect("home")

    registration_id = request.session.get("current_registration_id")
    if not registration_id:
        return redirect("test:user_register_link", link_id=link_id)

    try:
        reg = TestRegistration.objects.get(
            pk=registration_id, question_paper=paper, is_completed=False
        )
    except TestRegistration.DoesNotExist:
        return redirect("test:user_already_submitted")

    # POST: User accepts instructions and starts test
    if request.method == "POST":
        # Set flow status to 'instructed' and redirect to test
        request.session[get_session_key(link_id)] = "instructed"
        request.session.modified = True
        return redirect("test:user_test", link_id=link_id)

    # Calculate actual question count live from DB
    actual_total_questions = Question.objects.filter(section__question_paper=paper).count()

    # All checks passed
    return render(
        request, "user_test/instruction.html", {
            "link_id": link_id,
            "paper": paper,
            "actual_total_questions": actual_total_questions,
        }
    )


def user_test_view(request, link_id):
    """
    Handles the actual test display (GET) and submission (POST).
    """
    # --- FLOW CHECK ---
    redirect_response = check_flow_and_redirect(request, link_id, "user_test")
    if redirect_response:
        return redirect_response
    # --- END FLOW CHECK ---

    # --- GET ACCESS CHECK (Existing logic retained) ---
    try:
        paper_id = int(link_id)
        paper = get_object_or_404(QuestionPaper, pk=paper_id, is_public_active=True)
        registration_id = request.session.get("current_registration_id")

        # We MUST have a registration ID and valid paper
        if not registration_id:
            return redirect("test:user_register_link", link_id=link_id)

        # 1. Registration object fetch karein
        registration = get_object_or_404(
            TestRegistration, pk=registration_id, question_paper=paper
        )

    except Exception:
        return redirect("test:user_register_link", link_id=link_id)

    # ----------------------------------------------------------------------
    # CRITICAL BACK PREVENTION CHECK (DB check - is_completed)
    # ----------------------------------------------------------------------
    if registration.is_completed:
        return redirect("test:user_already_submitted")
    # ----------------------------------------------------------------------

    # We set status to 'in_progress' to clearly indicate the user has started the test.
    request.session[get_session_key(link_id)] = "in_progress"
    request.session.modified = True

    # --- POST SUBMISSION LOGIC ---
    if request.method == "POST":

        with transaction.atomic():

            # 1. Save user responses AND calculate score simultaneously
            correct_count = 0
            total_questions = paper.total_questions or 0
            saved_responses = []

            for key, value in request.POST.items():
                if key.startswith("question_"):
                    question_id = key.split("_")[1]
                    user_answer = value.strip()

                    try:
                        question = Question.objects.get(pk=question_id)
                        UserResponse.objects.create(
                            registration=registration,
                            question=question,
                            user_answer=user_answer,
                        )
                        # ✅ Calculate score for MCQ answers immediately (no AI needed)
                        if question.question_type == "MCQ" and user_answer:
                            if user_answer.lower() == question.answer.strip().lower():
                                correct_count += 1
                    except Question.DoesNotExist:
                        continue

            # 2. Calculate percentage and save score to DB immediately
            if total_questions > 0:
                percentage_score = round((correct_count / total_questions) * 100)
            else:
                percentage_score = 0

            # 3. Mark test complete AND save score in single save
            registration.is_completed = True
            registration.score = percentage_score
            registration.save(update_fields=["is_completed", "score"])

            # 4. Session clean up (important for back prevention)
            if "current_registration_id" in request.session:
                del request.session["current_registration_id"]
            if get_session_key(link_id) in request.session:
                request.session[get_session_key(link_id)] = "submitted"
            request.session.modified = True

        return redirect("test:user_already_submitted")

    # --- GET LOGIC (Rendering Questions - Existing logic retained) ---

    questions = (
        Question.objects.select_related("section")
        .filter(section__question_paper=paper)
        .order_by("section__order", "order")
    )

    sections_with_questions = {}

    for q in questions:
        section_title = q.section.title

        if section_title not in sections_with_questions:
            sections_with_questions[section_title] = {
                "title": section_title,
                "questions": [],
            }

        options_list = q.options if isinstance(q.options, list) else None

        if options_list:
            # उच्च प्राथमिकता: अगर options हैं, तो यह हमेशा MCQ होना चाहिए
            q_type = "MCQ"
        else:
            # अन्यथा, सीधे डेटाबेस में संग्रहीत प्रकार का उपयोग करें
            # (स्ट्रिंग को अपरकेस में बदलने से Consistency बनी रहती है)
            q_type = q.question_type.upper()

        sections_with_questions[section_title]["questions"].append(
            {"id": q.id, "text": q.text, "options": options_list, "type": q_type}
        )

    sections_list = list(sections_with_questions.values())
    actual_total_questions = sum(len(s["questions"]) for s in sections_list)

    context = {
        "paper": paper,
        "sections_list": sections_list,
        "link_id": link_id,
        "actual_total_questions": actual_total_questions,
    }
    return render(request, "user_test/test.html", context)


def user_already_submitted_view(request):
    """
    Shows the final 'Response Recorded' screen.
    """
    return render(request, "user_test/already_submitted.html")


# --- PROCTORING & ANTI-CHEATING ENDPOINTS ---

@csrf_exempt
def log_violation(request):
    """
    API endpoint to log a proctoring violation.

    COUNTABLE (increment total_violations + deduct proctoring score):
      - TAB_SWITCH       → user left the test tab  (-10 pts)
      - FULLSCREEN_EXIT  → user exited fullscreen   (-15 pts)
      - IDENTITY_CHECK_FAIL                         (-20 pts)

    NON-COUNTABLE (stored in DB for audit, but do NOT affect warning count):
      - TAB_SWITCH_RETURN  → user came back
      - CAMERA_DENIED      → camera blocked
      - CAMERA_ACTIVE      → camera granted
      - PERIODIC_CHECK     → routine snapshot
      - WINDOW_BLUR        → window lost focus (not a real tab switch)
      - (anything else)
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    registration_id = request.session.get("current_registration_id")
    if not registration_id:
        return JsonResponse({"error": "No active registration"}, status=403)

    try:
        from .models import TestViolation
        data = json.loads(request.body)
        violation_type = data.get("violation_type")
        duration = data.get("duration", 0.0)
        description = data.get("description", "")

        registration = get_object_or_404(TestRegistration, pk=registration_id)

        # --- Define which types actually COUNT as warnings ---
        COUNTABLE_VIOLATIONS = {
            'TAB_SWITCH',
            'FULLSCREEN_EXIT',
            'IDENTITY_CHECK_FAIL',
        }

        # Score deductions (only applied to countable violations)
        weights = {
            'TAB_SWITCH': 10.0,
            'FULLSCREEN_EXIT': 15.0,
            'IDENTITY_CHECK_FAIL': 20.0,
        }

        # Always log to DB for full audit trail
        violation_obj = TestViolation.objects.create(
            registration=registration,
            violation_type=violation_type,
            duration=duration,
            description=description
        )

        # Only increment warning counter for real violations
        if violation_type in COUNTABLE_VIOLATIONS:
            deduction = weights.get(violation_type, 0.0)
            registration.total_violations += 1
            registration.proctoring_score = max(0, float(registration.proctoring_score) - deduction)
            registration.save(update_fields=["total_violations", "proctoring_score"])
        else:
            # Refresh to get current values without modifying them
            registration.refresh_from_db(fields=["total_violations", "proctoring_score"])

        return JsonResponse({
            "status": "success",
            "violation_id": violation_obj.id,
            "total_violations": registration.total_violations,
            "proctoring_score": registration.proctoring_score,
            "counted": violation_type in COUNTABLE_VIOLATIONS,
        })

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
def upload_proctoring_media(request):
    """
    API endpoint to upload snapshots or video clips.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    registration_id = request.session.get("current_registration_id")
    if not registration_id:
        return JsonResponse({"error": "No active registration"}, status=403)

    try:
        from .models import TestViolation
        file_obj = request.FILES.get("file")
        if not file_obj:
            return JsonResponse({"error": "No file uploaded"}, status=400)

        registration = get_object_or_404(TestRegistration, pk=registration_id)
        violation_id = request.POST.get("violation_id")
        
        if violation_id:
            violation = get_object_or_404(TestViolation, pk=violation_id, registration=registration)
        else:
            # Periodic snapshot
            violation = TestViolation.objects.create(
                registration=registration,
                violation_type='PERIODIC_CHECK',
                description="Periodic proctoring snapshot"
            )

        if 'webm' in file_obj.name or 'mp4' in file_obj.name:
            violation.video_clip = file_obj
        else:
            violation.snapshot = file_obj
        
        violation.save()

        return JsonResponse({"status": "success", "violation_id": violation.id})

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
def log_cheating_event(request):
    """Fallback for legacy integrations."""
    return log_violation(request)
