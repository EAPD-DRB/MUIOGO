import { Base } from "../../Classes/Base.Class.js";
import { Osemosys } from "../../Classes/Osemosys.Class.js";

export default class ModelFile {

  static onLoad() {
    Promise.all([
      Base.getSession().catch(() => ({ session: "" })),
      Osemosys.readModelFile()
    ])
      .then(([sessionData, txt]) => {
        document.getElementById("osy-case").textContent = sessionData.session || "";
        if (!txt) {
          document.getElementById("equations").innerHTML =
            "<div class='alert alert-danger'>Unable to load model file.</div>";
          return;
        }
        const eqs = ModelFile.extractEquations(txt);
        if (!eqs.length) {
          document.getElementById("equations").innerHTML =
            "<div class='alert alert-warning'>No equations could be parsed from the model file.</div>";
          return;
        }
        ModelFile.renderEquations(eqs);
      });
  }

  // -----------------------------------------
  // Extract: objective + constraints
  // -----------------------------------------
  static extractEquations(txt) {
    const src = txt.replace(/\r/g, "");
    const eqs = [];

    // Objective
    const objRe = /(minimize|maximize)\s+([A-Za-z_]\w*)\s*:\s*([\s\S]*?)\s*;/i;
    const mObj = src.match(objRe);
    if (mObj) {
      eqs.push({
        section: "Objective",
        name: mObj[2],
        latex: ModelFile.gmplToLatex(mObj[3].trim())
      });
    }

    // Constraints
    const consRe = /s\.t\.\s*([A-Za-z_]\w*)\s*(\{[^}]*\})?\s*:\s*([\s\S]*?)(?=;)/gi;
    let m;
    while ((m = consRe.exec(src)) !== null) {
      eqs.push({
        section: ModelFile.detectSection(m[1]),
        name: m[1],
        latex: ModelFile.gmplToLatex(m[3].trim())
      });
    }

    return eqs;
  }

  // -----------------------------------------
  // Section assignment
  // -----------------------------------------
  static detectSection(name) {
    const n = name.toUpperCase();

    if (n.startsWith("EB")) return "Energy Balance";
        if (n.startsWith("E")) return "Emissions";
    if (n.startsWith("A") || n.startsWith("TAC") || n.startsWith("AAC")) return "Activity";
    if (n.startsWith("NC") || n.startsWith("TC") || n.startsWith("C")) return "Capacity";
    if (n.startsWith("S")) return "Storage";
    if (n.startsWith("UDC")) return "User-defined Constraints";
    return "Other";
  }

  // -----------------------------------------
  // GMPL --> LaTeX
  // -----------------------------------------
    static gmplToLatex(expr) {
        let s = expr;

        s = s.replace(/&&/g, " \\land ");
        s = s.replace(/<=/g, "\\le ")
            .replace(/>=/g, "\\ge ")
            .replace(/\*/g, "\\cdot ");

        // sum{}
        s = s.replace(/sum\s*\{([^}]*)\}/gi, (_, inside) => {
        const cleaned = inside
            .split(',')
            .map(p => p.trim().replace(/\s+in\s+/i," \\in "))
            .join(', ');
        return `\\sum_{${cleaned}}`;
        });

        // X[a,b]
        s = s.replace(/([A-Za-z_]\w*)\s*\[([^\]]+)\]/g, "\\mathrm{$1}_{ $2 }");

        // ukloni nove linije
        s = s.replace(/\n+/g, " ");

        return s;
    }

  // -----------------------------------------
  // FINAL RENDER + NUMERACIJA + LINIJE
  // -----------------------------------------
    static renderEquations(eqs) {
    const out = document.getElementById("equations");

    let html = "";
    let lastSection = "";
    let counter = 1;

    eqs.forEach((eq, i) => {
        const isNewSection = eq.section !== lastSection;

        // Deblja linija između sekcija (ali ne prije prve)
        if (isNewSection && i !== 0) {
        html += `<hr class="section-sep">`;
        }

        // Naslov sekcije ako je nova
        if (isNewSection) {
        html += `
            <h4 class="mt-2 mb-3" style="border-bottom:1px solid #ddd; padding-bottom:4px;">
            ${eq.section}
            </h4>
        `;
        lastSection = eq.section;
        }

        // Jednadžba + ručna numeracija + tanka linija nakon svake
        html += `
            <div class="mb-3" style="text-align:left;">
                <div class="text-secondary small mb-1">${eq.name}</div>

                <div class="math-wrapper">
                    $$
              
                    \\begin{align}
                        ${eq.latex}
                    \\end{align}
                    \\tag{${counter}}
           
                    $$
                </div>

                <hr class="eq-sep">
            </div>
            `;

            counter++;
        });

        out.innerHTML = html;
        if (window.MathJax?.typesetPromise) {
            window.MathJax.typesetPromise([out]).catch(() => {});
        }
    }
}
