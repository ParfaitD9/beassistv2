function createRow(pack) {
  let row = document.createElement("tr");
  row.id = pack.pk;
  row.innerHTML = `
  <td>
    <div class="d-flex px-2 py-1">
        <div class="d-flex flex-column justify-content-center">
        <a class="mb-0 text-sm h6" href="/pack/${pack.pk}">${pack.name}</a>
        <p class="text-xs text-secondary mb-0">${pack.customer.name}</p>
        </div>
    </div>
    </td>
    <td>
    <p class="text-xs font-weight-bold mb-0">${pack.price} $</p>
    <p class="text-xs text-secondary mb-0">${pack.subtasks.length} tâches</p>
    </td>
    <td class="align-middle text-center text-sm">
    <span class="badge badge-sm ${
      pack.customer.is_prospect
        ? "bg-gradient-secondary"
        : "bg-gradient-success"
    }"
        >${pack.customer.is_prospect ? "Soumission" : "Contrat"}</span>
    </td>
    <td class="align-middle text-center">
        <a
            href="javascript:;"
            class="nav-link text-body p-0"
            id="dropdownPackMenuButton-${pack.pk}"
            data-bs-toggle="dropdown"
            aria-expanded="false"
        >
            <i class="bi bi-three-dots cursor-pointer"></i>
        </a>
        <ul
            class="dropdown-menu dropdown-menu-end px-2 py-3 me-sm-n4"
            aria-labelledby="dropdownPackMenuButton-${pack.pk}"
        >
            <li>
                <a class="font-weight-bold dropdown-item border-radius-md" onclick="pack_facture(event)" data-bs-toggle="modal" data-bs-target="#facturePackModal">
                  Facturer ce contrat
                </a>
            </li>
            <li>
                <a class="font-weight-bold dropdown-item border-radius-md" href="/pack/${
                  pack.pk
                }">
                    Modifier ce contrat
                </a>
            </li>
            <li>
                <a class="font-weight-bold dropdown-item border-radius-md" onclick="pack_delete(event)">
                    Supprimer ce contrat
                </a>
            </li>
        </ul>
    </td>
    `;

  return row;
}

function fillPacks() {
  let table = document.querySelector("tbody#packsTbody");
  axios
    .get("/api/v1/packs")
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
var currentPack = {
  name: "",
  subtasks: [],
  customer: "",
};

$("input#add-subtask").click((e) => {
  if ($("input#inputSubtask").val() && $("input#inputValue").val()) {
    let sub = document.createElement("li");
    sub.textContent = `${$("input#inputSubtask").val()} ${$(
      "input#inputValue"
    ).val()}`;
    currentPack.subtasks.push({
      name: $("input#inputSubtask").val(),
      value: $("input#inputValue").val(),
    });
    $("ul#associes").append(sub);
    $("input#inputSubtask").val("");
    $("input#inputValue").val("");
  }
});

$("form#addPackModalForm").submit((e) => {
  e.preventDefault();
  currentPack.name = $("#inputName").val();
  currentPack.customer = $("#customers").val();

  let datas = new FormData();
  datas.append("data", JSON.stringify(currentPack));
  axios
    .post("/api/v1/pack/create", datas)
    .then((res) => {
      showModalAlert("addPackModal", res);
      $("ul#associes")
        .children()
        .each((i, obj) => {
          obj.remove();
        });
      currentPack = {
        name: "",
        subtasks: [],
        customer: "",
      };
      document
        .querySelector("tbody#packsTbody")
        .prepend(createRow(res.data.data));
    })
    .catch((err) => console.log(err));
});

$(document).ready((e) => {
  load_customers();
  load_subtasks();
  fillPacks();

  document.querySelector("a.nav-link.active").classList.remove("active");
  document.querySelectorAll("a.nav-link")[2].classList.add("active");
  /*
  setTimeout(() => {
    document.querySelectorAll("a.delete").forEach((el) => {
      el.addEventListener("click", (t) => {
        let row = el.parentElement.parentElement.parentElement.parentElement;
        axios
          .post(`/api/v1/pack/delete/${row.id}`)
          .then((res) => {
            console.log(res.data.message);
            row.remove();
          })
          .catch((err) => console.log(err));
      });
    });
    $("a.facture").click((e) => {
      let _id =
        e.target.parentNode.parentNode.parentNode.parentNode.parentNode.id;

      let f = document.querySelector("form#facturePackModalForm");
      f.querySelector("input#ref").value = _id;
    });
  }, 1000);
  */
});

document
  .querySelector("form#facturePackModalForm")
  .addEventListener("submit", (e) => {
    e.preventDefault();
    let data = new FormData(e.target);
    console.log(data);
    console.log(data.get("obj"));
    let pk = data.get("pk");
    data.delete("pk");
    axios
      .post(`/api/v1/pack/facture/${pk}`, data)
      .then((res) => {
        showModalAlert("facturePackModal", res);
      })
      .catch((err) => console.log(err));
  });

soumissionBox = document.querySelector("input#soumissionBox");
soumissionBox?.addEventListener("click", (e) => filter(e));

function filter(e) {
  axios
    .get("/api/v1/packs", {
      params: {
        soumissions: Number(soumissionBox.checked),
      },
    })
    .then((res) => fillTable(res))
    .catch((err) => console.log(err));
}

function fillTable(res) {
  let table = document.querySelector("tbody#packsTbody");
  table?.querySelectorAll("tr").forEach((el) => {
    el.remove();
  });

  if (res.data.success) {
    res.data.data.forEach((element) => {
      table?.appendChild(createRow(element));
    });
    /*
    document.querySelectorAll("a.delete").forEach((el) => {
      el.addEventListener("click", (t) => {
        let row = el.parentElement.parentElement.parentElement.parentElement;
        axios
          .post(`/api/v1/pack/delete/${row.id}`)
          .then((res) => {
            console.log(res.data.message);
            row.remove();
          })
          .catch((err) => console.log(err));
      });
    });
    $("a.facture").click((e) => {
      let _id =
        e.target.parentNode.parentNode.parentNode.parentNode.parentNode.id;

      let f = document.querySelector("form#facturePackModalForm");
      f.querySelector("input#ref").value = _id;
    });
    */
  }
}

function pack_delete(e) {
  let row = e.target.parentElement.parentElement.parentElement.parentElement;
  axios
    .post(`/api/v1/pack/delete/${row.id}`)
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

function pack_facture(e) {
  let row = e.target.parentElement.parentElement.parentElement.parentElement;
  let f = document.querySelector("form#facturePackModalForm");
  f.querySelector("input#ref").value = row.id;
}
