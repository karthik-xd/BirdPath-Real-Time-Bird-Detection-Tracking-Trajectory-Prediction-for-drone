import os
import sys
import shutil
import pypdf
import win32com.client

BASE_DIR = r"C:\dep learning"

def combine_ppts():
    combined_pptx = os.path.join(BASE_DIR, "BirdPath_Master_Combined_Presentation.pptx")
    combined_ppt_pdf = os.path.join(BASE_DIR, "BirdPath_Master_Combined_Presentation.pdf")
    master_ppt_pdf = os.path.join(BASE_DIR, "BirdPath_Full_Project_Master.pdf")
    
    # Check if already generated
    if os.path.exists(combined_pptx) and os.path.exists(combined_ppt_pdf):
        print("[1/5] Using existing combined PPTX & PDF...")
        return combined_pptx, combined_ppt_pdf

    print("[1/5] Combining PowerPoint Presentations...")
    ppt_app = win32com.client.Dispatch("PowerPoint.Application")
    
    master_pptx = os.path.join(BASE_DIR, "BirdPath_Full_Project_Master.pptx")
    explanation_pptx = os.path.join(BASE_DIR, "BirdPath_System_Explanation.pptx")
    
    pres = ppt_app.Presentations.Open(master_pptx, False, False, False)
    initial_count = pres.Slides.Count
    print(f"Master presentation initial slides: {initial_count}")
    
    pres.SaveAs(master_ppt_pdf, 32)
    print(f"Saved: {master_ppt_pdf}")
    
    pres.Slides.InsertFromFile(explanation_pptx, initial_count)
    total_slides = pres.Slides.Count
    print(f"Combined presentation total slides: {total_slides}")
    
    pres.SaveCopyAs(combined_pptx)
    print(f"Saved combined PPTX: {combined_pptx}")
    
    pres.SaveAs(combined_ppt_pdf, 32)
    print(f"Saved combined PPT as PDF: {combined_ppt_pdf}")
    
    pres.Close()
    ppt_app.Quit()
    return combined_pptx, combined_ppt_pdf

def combine_pdfs(combined_ppt_pdf):
    print("\n[2/5] Combining Documentation PDFs...")
    guide_pdf = os.path.join(BASE_DIR, "BirdPath_Complete_Concepts_Algorithms_Functions_Guide.pdf")
    params_pdf = os.path.join(BASE_DIR, "BirdPath_Full_System_Parameters_Master.pdf")
    expl_pdf = os.path.join(BASE_DIR, "BirdPath_System_Explanation.pdf")
    
    # Combined Documentation (Concepts Guide + System Parameters + System Explanation)
    doc_writer = pypdf.PdfWriter()
    
    page_offset = 0
    # 1. Guide
    reader_guide = pypdf.PdfReader(guide_pdf)
    doc_writer.add_outline_item("Part 1: Complete Concepts, Algorithms & Functions Guide", page_offset)
    doc_writer.append(guide_pdf)
    page_offset += len(reader_guide.pages)
    
    # 2. Parameters
    reader_params = pypdf.PdfReader(params_pdf)
    doc_writer.add_outline_item("Part 2: Full System Parameters & Architecture Specification", page_offset)
    doc_writer.append(params_pdf)
    page_offset += len(reader_params.pages)
    
    # 3. Explanation
    reader_expl = pypdf.PdfReader(expl_pdf)
    doc_writer.add_outline_item("Part 3: BirdPath System & Pipeline Walkthrough", page_offset)
    doc_writer.append(expl_pdf)
    page_offset += len(reader_expl.pages)
    
    combined_docs_pdf = os.path.join(BASE_DIR, "BirdPath_Master_Combined_Documentation.pdf")
    with open(combined_docs_pdf, "wb") as f:
        doc_writer.write(f)
    print(f"Saved combined docs PDF: {combined_docs_pdf} ({page_offset} pages)")
    
    # ULTIMATE ALL-IN-ONE (Executive Master Presentation Slides + All Technical Documentation)
    print("\n[3/5] Creating ULTIMATE ALL-IN-ONE Combined Master PDF (All PPTs + All PDFs)...")
    ultimate_writer = pypdf.PdfWriter()
    curr_page = 0
    
    # Section 1: Presentation Slides
    reader_ppt = pypdf.PdfReader(combined_ppt_pdf)
    ppt_pages = len(reader_ppt.pages)
    ultimate_writer.add_outline_item("Section I: Master Presentation Slides Deck (33 Slides)", curr_page)
    ultimate_writer.add_outline_item("• Master Architecture & Pipeline (Slides 1-22)", curr_page)
    ultimate_writer.add_outline_item("• Core System Deep-Dive & Hardware (Slides 23-33)", curr_page + 22)
    ultimate_writer.append(combined_ppt_pdf)
    curr_page += ppt_pages
    
    # Section 2: Concepts, Algorithms & Functions Specification
    ultimate_writer.add_outline_item("Section II: Concepts, Algorithms & Functions Specification", curr_page)
    ultimate_writer.append(guide_pdf)
    curr_page += len(reader_guide.pages)
    
    # Section 3: Full System Parameters Specification
    ultimate_writer.add_outline_item("Section III: Full System Parameters Specification", curr_page)
    ultimate_writer.append(params_pdf)
    curr_page += len(reader_params.pages)
    
    # Section 4: System Explanation & Architecture Guide
    ultimate_writer.add_outline_item("Section IV: System Explanation & Deep Architecture Guide", curr_page)
    ultimate_writer.append(expl_pdf)
    curr_page += len(reader_expl.pages)
    
    ultimate_pdf = os.path.join(BASE_DIR, "BirdPath_ULTIMATE_ALL_IN_ONE_MASTER.pdf")
    with open(ultimate_pdf, "wb") as f:
        ultimate_writer.write(f)
    print(f"Saved ULTIMATE Combined Master PDF: {ultimate_pdf} ({curr_page} pages)")
    
    # Also copy to static folder for web studio access
    static_dir = os.path.join(BASE_DIR, "computer learning", "static")
    if os.path.exists(static_dir):
        shutil.copy2(ultimate_pdf, os.path.join(static_dir, "BirdPath_ULTIMATE_ALL_IN_ONE_MASTER.pdf"))
        shutil.copy2(combined_docs_pdf, os.path.join(static_dir, "BirdPath_Master_Combined_Documentation.pdf"))
        shutil.copy2(combined_ppt_pdf, os.path.join(static_dir, "BirdPath_Master_Combined_Presentation.pdf"))
        print("Copied combined PDFs to computer learning/static/")
    
    return combined_docs_pdf, ultimate_pdf

if __name__ == "__main__":
    combined_pptx, combined_ppt_pdf = combine_ppts()
    combined_docs_pdf, ultimate_pdf = combine_pdfs(combined_ppt_pdf)
    print("\n[4/5] Inspecting final generated files...")
    reader = pypdf.PdfReader(ultimate_pdf)
    print(f"ULTIMATE ALL-IN-ONE PDF Total Pages: {len(reader.pages)}")
    reader_docs = pypdf.PdfReader(combined_docs_pdf)
    print(f"Combined Documentation PDF Total Pages: {len(reader_docs.pages)}")
    reader_ppt = pypdf.PdfReader(combined_ppt_pdf)
    print(f"Combined Presentation PDF Total Pages: {len(reader_ppt.pages)}")
    print("\n[5/5] All operations completed successfully!")
