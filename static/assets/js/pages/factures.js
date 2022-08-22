$(document).ready((e) => {
  document.querySelector("a.nav-link.active").classList.remove("active");
  document.querySelectorAll("a.nav-link")[3].classList.add("active");
  load_customers();
  load_subtasks();
  fillFactures();

  /*
  setTimeout(() => {
    document.querySelectorAll("a.delete").forEach((el) => {
      el.addEventListener("click", (t) => {
        let row = el.parentElement.parentElement.parentElement.parentElement;
        if (window.confirm(`Voulez-vous supprimer la facture ${row.id} ?`)) {
          axios
            .post(`/api/v1/facture/delete/${row.id}`)
            .then((res) => {
              if (res.data.success) {
                row.remove();
              } else {
                window.alert(res.data.message);
              }
            })
            .catch((err) => console.log(err));
        }
      });
    });
    
    document.querySelectorAll("a.send").forEach((el) => {
      el.addEventListener("click", (t) => {
        let row = el.parentElement.parentElement.parentElement.parentElement;
        document
          .querySelector("form#sendFactureModalForm")
          .querySelector("input#ref").value = row.id;
      });
    });
  }, 1000);
  */
});

var currentFacture = {
  obj: "",
  subtasks: [],
  customer: "",
};

function createRow(facture) {
  let row = document.createElement("tr");
  row.id = facture.hash;
  row.innerHTML = `
    <td>
        <div class="d-flex px-2 py-1">
        <div class="d-flex flex-column justify-content-center">
            <a href="/api/v1/facture/view/${
              facture.hash
            }" class="mb-0 text-sm font-weight-bold" target="_blank">${
    facture.hash
  }</a>
            <p class="text-xs text-secondary mb-0">
            ${facture.date}
            </p>
        </div>
        </div>
    </td>
    <td>
        <p class="text-xs font-weight-bold mb-0">${facture.customer.name}</p>
    </td>
    <td class="align-middle text-center">
        <span class="text-secondary text-xs font-weight-bold"
        >${facture.cout} $</span
        >
    </td>
    <td class="align-middle text-center text-sm">
        <span class="badge badge-sm ${
          !facture.customer.is_prospect
            ? "bg-gradient-success"
            : "bg-gradient-secondary"
        }"
        >${facture.sent ? "Oui" : "Non"}</span>
    </td>
    <td class="align-middle text-center">
        <a
            href="javascript:;"
            class="nav-link text-body p-0"
            id="dropdownFactureMenuButton-${facture.hash}"
            data-bs-toggle="dropdown"
            aria-expanded="false"
        >
            <i class="bi bi-three-dots cursor-pointer"></i>
        </a>
        <ul
            class="dropdown-menu dropdown-menu-end px-2 py-3 me-sm-n4"
            aria-labelledby="dropdownFactureMenuButton-${facture.hash}"
        >
            <li>
            <a class="font-weight-bold dropdown-item border-radius-md send" onclick="facture_send(event)" data-bs-toggle="modal" data-bs-target="#sendFactureModal">
                Envoyer cette facture
            </a>
            </li>
            <li>
            <a class="font-weight-bold dropdown-item border-radius-md disabled">
                Classer cette facture
            </a>
            </li>
            <li>
            <a class="font-weight-bold dropdown-item border-radius-md delete" onclick="facture_delete(event)">
                Supprimer cette facture
            </a>
            </li>        
        </ul>
    </td>
  `;
  return row;
}

function fillFactures() {
  let table = document.querySelector("tbody#facturesTbody");
  axios
    .get("/api/v1/factures")
    .then((res) => {
      if (res.data.success) {
        table?.querySelectorAll("tr").forEach((el) => {
          el.remove();
        });

        res.data.data.forEach((element) => {
          table?.appendChild(createRow(element));
        });
      }
    })
    .catch((err) => console.log(err));
}

$("form#sendFactureModalForm").submit((e) => {
  e.preventDefault();
  let data = new FormData(e.target);
  let pk = data.get("pk");
  data.delete("pk");
  axios
    .post(`/api/v1/facture/send/${pk}`, data)
    .then((res) => {
      if (res.data.success) {
        showModalAlert("sendFactureModal", res);
        e.reset();
      }
    })
    .catch((err) => console.log(err));
});
$("input#add-subtask").click((e) => {
  if ($("input#inputSubtask").val() && $("input#inputValue").val()) {
    let sub = document.createElement("li");
    sub.textContent = `${$("input#inputSubtask").val()} ${$(
      "input#inputValue"
    ).val()}`;
    currentFacture.subtasks.push({
      name: $("input#inputSubtask").val(),
      value: $("input#inputValue").val(),
    });
    $("ul#associes").append(sub);
    $("input#inputSubtask").val("");
    $("input#inputValue").val("");
  }
});

$("form#addFactureModalForm").submit((e) => {
  e.preventDefault();
  currentFacture.obj = $("#inputName").val();
  currentFacture.customer = $("#customers").val();

  let datas = new FormData();
  datas.append("data", JSON.stringify(currentFacture));
  axios
    .post("/api/v1/facture/create", datas)
    .then((res) => {
      showModalAlert("addFactureModal", res);
      $("ul#associes")
        .children()
        .each((i, obj) => {
          obj.remove();
        });
      currentFacture = {
        name: "",
        subtasks: [],
        customer: "",
      };
      document
        .querySelector("tbody#facturesTbody")
        .prepend(createRow(res.data.data));
    })
    .catch((err) => console.log(err));
});

let soumissionBox = document.querySelector("input#soumissionBox");
let notSentBox = document.querySelector("input#notSentBox");
let searchBox = document.querySelector("button#searchButton");
let searchBar = document.querySelector("input#searchBar");

soumissionBox?.addEventListener("click", (e) => filter(e));
notSentBox?.addEventListener("click", (e) => filter(e));
searchBox?.addEventListener("click", (e) => filter(e));
searchBar?.addEventListener("change", (e) => filter(e));

function filter(e) {
  axios
    .get("/api/v1/factures", {
      params: {
        soumissions: Number(soumissionBox.checked),
        notsent: Number(notSentBox.checked),
        hash: document.querySelector("input#searchBar").value,
      },
    })
    .then((res) => fillTable(res))
    .catch((err) => console.log(err));
}

function fillTable(res) {
  let table = document.querySelector("tbody#facturesTbody");
  table?.querySelectorAll("tr").forEach((el) => {
    el.remove();
  });

  if (res.data.success) {
    res.data.data.forEach((element) => {
      table?.appendChild(createRow(element));
    });
  }
}

function facture_send(e) {
  let row = e.target.parentElement.parentElement.parentElement.parentElement;
  document
    .querySelector("form#sendFactureModalForm")
    .querySelector("input#ref").value = row.id;
}

function facture_delete(e) {
  let row = e.target.parentElement.parentElement.parentElement.parentElement;
  if (window.confirm(`Voulez-vous supprimer la facture ${row.id} ?`)) {
    axios
      .post(`/api/v1/facture/delete/${row.id}`)
      .then((res) => {
        if (res.data.success) {
          console.log(res.data.message);
          row.remove();
        } else {
          window.alert(res.data.message);
        }
      })
      .catch((err) => console.log(err));
  }
}
